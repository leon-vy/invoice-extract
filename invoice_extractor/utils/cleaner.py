import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Cleaners:
    def __init__(self):
        pass

    def clean_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and sanitize column names to ensure compatibility with BigQuery.
        """
        logging.info("Cleaning column names...")
        df.columns = df.columns.astype(str).str.replace('[^a-zA-Z0-9]', '_', regex=True)

        cols = pd.Series(df.columns)
        for dup in cols[cols.duplicated()].unique():
            indices = cols[cols == dup].index
            cols[indices] = [f"{dup}_{i}" if i != 0 else dup for i in range(len(indices))]

        df.columns = cols
        return df
    
    def split_desc(self, descr: str) -> str:
        """
        Splitting the description into two parts based on the first occurrence of ' - '.
        """
        first_part = descr.split(' - ')[0]
        return first_part