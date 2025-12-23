from typing import List
import pandas as pd
from pydantic import BaseModel
from invoice_extractor.core.extractors import BaseInvoiceExtractor
from invoice_extractor.extractor.sa.output import SAInvoiceDataOutput
from invoice_extractor.utils.bigq_handler import BigQueryHandler
from invoice_extractor.core import settings

class SAInvoiceExtractor(BaseInvoiceExtractor):
    def __init__(self, openai_client: str, model: str, prompt: str, output_model: BaseModel):
        super().__init__(openai_client, model, prompt, output_model)

    def process_data(self, invoices: List[SAInvoiceDataOutput]) -> pd.DataFrame:
        """Traitement spécifique SA360"""
        flattened_data = []
        for entry in invoices:
            for item in entry['rows']:
                inv_dict = item.dict()
                flattened_data.append(inv_dict)
        
        bigq_handler = BigQueryHandler(
            creds=str(settings.service_account_provider), 
            dataset_id=settings.dataset_id_pads
        )
        bigq_handler.append_data(pd.DataFrame(flattened_data), "sa_provider")
        
        return pd.DataFrame(flattened_data)


