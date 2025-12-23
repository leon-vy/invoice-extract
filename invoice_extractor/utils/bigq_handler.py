import pandas as pd
from google.cloud import bigquery
import logging
from invoice_extractor.core.config import TYPE_MAP
from .cleaner import Cleaners
from typing import List


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BigQueryHandler(Cleaners):
    """
    A class to handle interactions with Google BigQuery.
    """
    
    def __init__(self, creds: str, dataset_id: str):
        """
        Initialize BigQueryHandler with credentials and dataset ID.
        """
        self.creds = creds
        self.dataset_id = dataset_id
        self.client = self._initialize_client()

    def _initialize_client(self):
        """
        Initialize BigQuery client using the provided credentials.
        """
        logging.info("Initializing BigQuery client...")
        try:
            return bigquery.Client.from_service_account_json(self.creds)
        except Exception as e:
            logging.error(f"Error initializing BigQuery client: {e}")
            raise

    def generate_schema(self, df: pd.DataFrame) -> List[bigquery.SchemaField]:
        """
        Generate BigQuery schema based on the DataFrame's column types.
        """
        logging.info("Generating BigQuery schema...")
        schema = []
        for col in df.columns:
            try:
                dtype_str = str(df[col].dtype)
                bq_type = TYPE_MAP.get(dtype_str, 'STRING')
                schema.append(bigquery.SchemaField(col.lower(), bq_type))
            except Exception as e:
                logging.warning(f"Failed to process column {col}: {e}")
        return schema

    def create_or_get_table(self, table_id: str, schema: List[bigquery.SchemaField]) -> bigquery.TableReference:
        """
        Create a BigQuery table if it doesn't exist, otherwise return the existing table.
        """
        logging.info(f"Ensuring table {table_id} exists in dataset {self.dataset_id}...")
        table_ref = self.client.dataset(self.dataset_id).table(table_id)
        try:
            existing_table = self.client.get_table(table_ref)
            logging.info(f"Table {table_id} already exists.")
            return table_ref
        except Exception:
            logging.info(f"Table {table_id} does not exist. Creating new table...")
            table = bigquery.Table(table_ref, schema=schema)
            self.client.create_table(table)
            logging.info(f"Table {table_id} created successfully.")
            return table_ref
    
    def update_table_schema(self, table_id: str, new_schema: List[bigquery.SchemaField]) -> None:
        """
        Update table schema to include new fields if they don't exist.
        """
        table_ref = self.client.dataset(self.dataset_id).table(table_id)
        try:
            table = self.client.get_table(table_ref)
            existing_fields = {field.name.lower(): field for field in table.schema}
            new_fields = []
            
            for field in new_schema:
                if field.name.lower() not in existing_fields:
                    new_fields.append(field)
                    logging.info(f"Adding new field: {field.name} ({field.field_type})")
            
            if new_fields:
                table.schema = list(table.schema) + new_fields
                self.client.update_table(table, ["schema"])
                logging.info(f"Updated table schema with {len(new_fields)} new field(s).")
        except Exception as e:
            logging.warning(f"Could not update table schema: {e}")
    
    def align_dataframe_to_schema(self, df: pd.DataFrame, table_id: str) -> pd.DataFrame:
        """
        Align DataFrame columns with existing table schema.
        """
        table_ref = self.client.dataset(self.dataset_id).table(table_id)
        try:
            table = self.client.get_table(table_ref)
            existing_columns = {field.name.lower(): field.name for field in table.schema}
            
            df_columns_lower = {col.lower(): col for col in df.columns}
            
            aligned_df = pd.DataFrame()
            for bq_col_lower, bq_col_name in existing_columns.items():
                if bq_col_lower in df_columns_lower:
                    aligned_df[bq_col_name] = df[df_columns_lower[bq_col_lower]]
                else:
                    aligned_df[bq_col_name] = None
            
            for df_col_lower, df_col_name in df_columns_lower.items():
                if df_col_lower not in existing_columns:
                    aligned_df[df_col_name] = df[df_col_name]
            
            return aligned_df
        except Exception as e:
            logging.warning(f"Could not align DataFrame to schema: {e}. Using original DataFrame.")
            return df

    def load_data(self, df: pd.DataFrame, table_id: str, write_disposition: bigquery.WriteDisposition) -> None:
        """
        Load data into a BigQuery table with the specified write disposition.
        """
        if df.empty:
            logging.warning(f"DataFrame is empty. Skipping load to {table_id}.")
            return
        
        if len(df.columns) == 0:
            logging.warning(f"DataFrame has no columns. Skipping load to {table_id}.")
            return
        
        df = self.clean_column_names(df)
        
        for col in df.columns:
            if str(df[col].dtype) == 'Int64':
                df[col] = df[col].astype('float64')
            elif str(df[col].dtype) == 'Int32':
                df[col] = df[col].astype('float64')
            elif str(df[col].dtype).startswith('Int'):
                df[col] = df[col].astype('float64')
        
        schema = self.generate_schema(df)
        
        if not schema:
            logging.error(f"Generated schema is empty. Cannot load data to {table_id}.")
            raise ValueError("Cannot load data with empty schema.")
        
        table_ref = self.create_or_get_table(table_id, schema)
        
        if write_disposition == bigquery.WriteDisposition.WRITE_APPEND:
            try:
                existing_table = self.client.get_table(table_ref)
                existing_columns = {field.name.lower() for field in existing_table.schema}
                df_columns = {col.lower() for col in df.columns}
                
                if df_columns != existing_columns:
                    logging.info("Schema mismatch detected. Updating table schema and aligning DataFrame...")
                    self.update_table_schema(table_id, schema)
                    df = self.align_dataframe_to_schema(df, table_id)
                    existing_table = self.client.get_table(table_ref)
                    schema = existing_table.schema
            except Exception as e:
                logging.warning(f"Could not check/update schema: {e}. Using autodetect.")
                schema = None

        logging.info(f"Loading {len(df)} row(s) into BigQuery table {table_id}...")
        job_config = bigquery.LoadJobConfig(
            write_disposition=write_disposition,
            autodetect=(schema is None)
        )
        if schema:
            job_config.schema = schema
        
        job = self.client.load_table_from_dataframe(df, table_ref, job_config=job_config)

        try:
            job.result()
            logging.info("Data loaded successfully.")
        except Exception as e:
            logging.error(f"Error loading data: {e}")
            raise

    def insert_data(self, df: pd.DataFrame, table_id: str) -> None:
        """
        Insert data into BigQuery, overwriting existing data in the table.
        """
        logging.info("Inserting data (overwriting existing table)...")
        self.load_data(df, table_id, bigquery.WriteDisposition.WRITE_TRUNCATE)

    def append_data(self, df,table_id):
        """
        Append data to an existing BigQuery table, skipping rows with invoice_number that already exist.
        """
        logging.info("Appending data to existing table...")
        
        if df.empty:
            logging.warning("DataFrame is empty. Nothing to append.")
            return
        
        if len(df.columns) == 0:
            logging.warning("DataFrame has no columns. Nothing to append.")
            return
        
        df = self.clean_column_names(df)
        
        if 'invoice_number' not in df.columns:
            logging.warning("Column 'invoice_number' not found in DataFrame. Appending all data.")
            self.load_data(df, table_id, bigquery.WriteDisposition.WRITE_APPEND)
            return
        
        table_ref = self.client.dataset(self.dataset_id).table(table_id)
        try:
            table = self.client.get_table(table_ref)
            logging.info(f"Table {table_id} exists. Checking for existing invoice_numbers...")
            
            query = f"""
                SELECT DISTINCT invoice_number
                FROM `{self.client.project}.{self.dataset_id}.{table_id}`
                WHERE invoice_number IS NOT NULL
            """
            existing_invoices_df = self.client.query(query).to_dataframe()
            
            if not existing_invoices_df.empty:
                existing_invoice_numbers = set(existing_invoices_df['invoice_number'].astype(str).str.lower())
                logging.info(f"Found {len(existing_invoice_numbers)} existing invoice_number(s) in table.")
                
                # Filter out rows with existing invoice_numbers
                # Convert to lowercase for case-insensitive comparison
                df['invoice_number_lower'] = df['invoice_number'].astype(str).str.lower()
                initial_count = len(df)
                df = df[~df['invoice_number_lower'].isin(existing_invoice_numbers)]
                df = df.drop(columns=['invoice_number_lower'])
                
                filtered_count = len(df)
                skipped_count = initial_count - filtered_count
                
                if skipped_count > 0:
                    logging.info(f"Skipped {skipped_count} row(s) with existing invoice_number(s).")
                
                if filtered_count == 0:
                    logging.info("No new data to append. All invoice_numbers already exist.")
                    return
                
                logging.info(f"Appending {filtered_count} new row(s)...")
            else:
                logging.info("No existing invoice_numbers found. Appending all data.")
                
        except Exception as e:
            logging.info(f"Table {table_id} does not exist or error querying: {e}. Appending all data.")
        
        self.load_data(df, table_id, bigquery.WriteDisposition.WRITE_APPEND)


# if __name__ == "__main__":
#     df = pd.read_csv("your selected path")
#     table_id = "your selected table id"
#     credentials = "your selected credentials path"
#     dataset_id = "your selected dataset id"
#     bigq_handler = BigQueryHandler(creds=credentials, dataset_id=dataset_id)
#     bigq_handler.append_data(df, table_id)