from google.cloud import bigquery
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClientDataFetcher:
    def __init__(self, service_account):
        self.creds_path = service_account

    def querying(self, query_: str, month: str, service_account_path=None) -> pd.DataFrame:
        """
        Query BigQuery with optional service account path.
        If service_account_path is not provided, uses self.creds_path.
        
        Args:
            query_: SQL query string
            month: Month parameter value (STRING format)
            service_account_path: Optional path to service account JSON file
        """
        creds_to_use = service_account_path if service_account_path else self.creds_path
        client = bigquery.Client.from_service_account_json(creds_to_use)
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("month", "STRING", month)
            ]
        )
        result_df = client.query(query_, job_config=job_config).to_dataframe()
        return result_df

