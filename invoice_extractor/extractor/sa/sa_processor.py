from typing import Any
import pandas as pd
import logging
from invoice_extractor.extractor.sa.sa_extractor import SAInvoiceExtractor
from invoice_extractor.core import settings
import os
from pathlib import Path
from invoice_extractor.extractor.sa.output import SAInvoiceDataOutput
from invoice_extractor.utils.bigq_handler import BigQueryHandler


from invoice_extractor.extractor.sa.retrieve_file_mail.mail_drive import GmailToDrive
from invoice_extractor.extractor.sa.retrieve_file_mail.configs import MAPPING_INVOICES_TO_DRIVE_GGL,EMAILS 
import openai
from invoice_extractor.extractor.sa.prompting import sa_prompt

from invoice_extractor.core import BaseProcessor, ProcessorRegistry, settings

logger = logging.getLogger(__name__)

@ProcessorRegistry.register("SA")
class SAProcessor(BaseProcessor):
    def __init__(self, openai_client: Any = None, model: str = "gpt-4o", prompt: str = ""):
        super().__init__("SA")
        self.openai_client = openai_client or openai.OpenAI(api_key=settings.api_key_openai)
        self.model = model
        self.prompt = prompt or sa_prompt
        self.bigq_handler = BigQueryHandler(
            creds=str(settings.service_account_provider), 
            dataset_id=settings.dataset_id_pads
        )
    def process_extractor(
        self,
        invoices_path: str,
        output_temp_path: str = "",
    ) -> pd.DataFrame:

        logger.info(f"Processing SA360...")
        
        if not os.path.exists(invoices_path):
            logger.error(f"Le répertoire des factures n'existe pas: {invoices_path}")
            raise FileNotFoundError(f"Directory not found: {invoices_path}")
        
        pdf_files = list(Path(invoices_path).rglob("*.pdf")) + list(Path(invoices_path).rglob("*.PDF"))
        logger.info(f"Trouvé {len(pdf_files)} fichier(s) PDF dans {invoices_path}")
        
        if len(pdf_files) == 0:
            logger.warning(f"Aucun fichier PDF trouvé dans {invoices_path}")
            return pd.DataFrame()
        
        os.makedirs(output_temp_path, exist_ok=True)
        logger.info(f"Répertoire de sortie temporaire: {output_temp_path}")
        
        extractor = SAInvoiceExtractor(
            openai_client=self.openai_client,
            model=self.model,
            prompt=self.prompt,
            output_model=SAInvoiceDataOutput
        )
        
        invoices = extractor.process_batch(invoices_path, output_temp_path)
        
        if not invoices:
            logger.warning("Aucune facture extraite!")
            return pd.DataFrame()
        
        return extractor.process_data(invoices)
    
    def process_mail_data(self):
        """Process mail data using Gmail to Drive functionality"""
        logger.info("Processing mail data...")
        
        for email in EMAILS:
            for index, mapping in enumerate(MAPPING_INVOICES_TO_DRIVE_GGL):
                print(f"/ Processing of {mapping['drive_name']} ({index + 1} of {len(MAPPING_INVOICES_TO_DRIVE_GGL[0])}) /")
                GmailToDrive(
                    user_to_impers=email,
                    subjects=mapping['subject'],
                    drive_folder_id=mapping['folder_id'],
                    label_name=mapping['label_tag'],
                    local_folder_name=mapping['local_folder']
                ).process_emails()
    
    def run(self, invoices_path: str = "", output_temp_path: str = ""):
        """Main function to run both mail processing and invoice extraction"""
        output_temp_path = output_temp_path or str(settings.output_temp)
        logger.info("Starting SA processor...")
        
        # Process mail data first
        self.process_mail_data()
        
        # Process invoices
        result_sa = self.process_extractor(invoices_path, output_temp_path)
        
        # Upload to BigQuery only if we have data
        if result_sa is not None and not result_sa.empty:
            logger.info(f"Uploading {len(result_sa)} row(s) to BigQuery...")
            self.bigq_handler.append_data(result_sa, "sa_provider")
        else:
            logger.warning("No data to upload to BigQuery.")
        
