from invoice_extractor.core import BaseProcessor, ProcessorRegistry, settings
from invoice_extractor.extractor.amazon_api.adsp_controller import AdspController
from invoice_extractor.extractor.amazon_api.config import logger
from invoice_extractor.extractor.amazon_api.utils import is_date_in_range, transform
import pandas as pd
from invoice_extractor.utils.bigq_handler import BigQueryHandler

@ProcessorRegistry.register("ADSP")
class ADSPProcessor(BaseProcessor):
    def __init__(self):
        """Initialize ADSP processor with BigQuery handler."""
        super().__init__("ADSP")
        try:
            self.bigq_handler = BigQueryHandler(
                creds=str(settings.service_account_provider), 
                dataset_id=settings.dataset_id_pads
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de BigQuery: {e}")
            raise

    def processor(self, start_date: str, end_date: str, regions: list[str]):
        """Fonction principale qui orchestre l'extraction complète."""
        logger.info(f"Début du téléchargement – période : {start_date} → {end_date}")

        all_dataframes = []

        for region in regions:
            api_amazon = AdspController(region)
            profiles = api_amazon.get_profiles()
            
            for profile in profiles:
                profile_id = str(profile["profileId"])
                account_name = profile.get("accountInfo", {}).get("name", "Inconnu")
                
                

                invoices = api_amazon.invoices_filter(
                    profile_id, start_date=start_date, end_date=end_date
                )

                for inv in invoices:
                    invoice_id = inv.get("id") or inv.get("invoiceId")
                    if not invoice_id:
                        continue

                    invoice_date_from_summary = inv.get("invoiceDate") or inv.get("date")
                    if not is_date_in_range(invoice_date_from_summary, start_date, end_date):
                        continue

                    logger.info(f"[{region}] {account_name} → Facture {invoice_id}")

                    try:
                        json_data = api_amazon.invoice_details(profile_id, invoice_id)
                        invoice_summary = json_data.get("payload", {}).get("invoiceSummary", {})

                        # Vérification de la date complète si différente
                        if (
                            invoice_summary.get("invoiceDate")
                            and invoice_summary.get("invoiceDate") != invoice_date_from_summary
                        ):
                            if not is_date_in_range(invoice_summary.get("invoiceDate"), start_date, end_date):
                                logger.warning(
                                    f"[{region}] Facture {invoice_id} exclue après récupération "
                                    f"(date complète: {invoice_summary.get('invoiceDate')} "
                                    f"hors intervalle {start_date} - {end_date})"
                                )
                                continue

                        df = transform(json_data, region, profile_id, account_name)
                        
                        if not df.empty:
                            all_dataframes.append(df)
                            logger.info(
                                f"[{region}] Facture {invoice_id} transformée en DataFrame "
                                f"({len(df)} lignes)"
                            )

                    except Exception as e:
                        logger.error(f"ERREUR {invoice_id} : {e}")

        if all_dataframes:
            try:
                combined_df = pd.concat(all_dataframes, ignore_index=True)
                logger.info(f"Total de {len(combined_df)} lignes à charger dans BigQuery")
                
                self.bigq_handler.append_data(combined_df, "adsp_provider")
                logger.info("✅ Processus terminé avec succès!")
            except Exception as e:
                logger.error(f"Erreur lors de l'ajout des données dans BigQuery: {e}")

    def run(self, start_date: str = "", end_date: str = "", regions: list[str] = None):
        """Main function to run ADSP processor with default parameters if not provided."""
        if regions is None:
            regions = ["US", "EU"]
        
        if not start_date or not end_date:
            from datetime import datetime
            
            today = datetime.now()
            start_of_month = today.replace(day=1)
            
            start_date = start_of_month.strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")
        
        logger.info("Starting ADSP processor...")
        self.processor(start_date=start_date, end_date=end_date, regions=regions)


# # Quick runner
# if __name__ == "__main__":
#     processor = ADSPProcessor()
#     processor.run(regions=["US", "EU"])
