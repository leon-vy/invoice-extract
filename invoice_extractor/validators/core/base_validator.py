from pathlib import Path
from invoice_extractor.validators.core.data_fetcher import ClientDataFetcher
from invoice_extractor.utils.bigq_handler import BigQueryHandler
from invoice_extractor.core import settings

from abc import ABC, abstractmethod
import numpy as np

class BaseApproval(ClientDataFetcher):
    def __init__(self, service_account, query_bigq, query_provider, dataset_id):
        super().__init__(service_account)
        self.query_bigq = query_bigq
        self.query_provider = query_provider
        self.service_account_pads = str(settings.service_account_pads)
        self.service_account_provider = str(settings.service_account_provider)
        self.bigq_handler = BigQueryHandler(
            creds=self.service_account_provider, 
            dataset_id=dataset_id or settings.dataset_id_pads
        )

    def fetch_bigq_data(self, month):
        """
        Fetches approval data from BigQuery using SERVICE_ACCOUNT_PADS.
        """
        return self.querying(self.query_bigq, month, self.service_account_pads)

    def fetch_provider_data(self, month):
        """
        Fetches provider data from BigQuery using SERVICE_ACCOUNT_PROVIDER.
        """
        return self.querying(self.query_provider, month, self.service_account_provider)

    @abstractmethod
    def cleaning_data(self):
        """
        Cleans the data.
        """
        pass

    def apply_rules(self, data):
        # Calculate Delta Value
        data['Amount_Delta_Value'] = data['Amount_BQ'] - data['Amount_Invoice']
        data['Amount_Delta_Percentage'] = np.where(
            data['Amount_BQ'] != 0,
            (data['Amount_Delta_Value'] * 100) / data['Amount_BQ'],
            0
        )
        data['Amount_Delta_Percentage'] = data['Amount_Delta_Percentage'].round(2)
        data = data[~((data['Amount_BQ'] == 0) & (data['Amount_Invoice'] == 0))].copy()

        data['Auto_Validation_Status'] = ''

        has_invoice = data['Invoice_Number'].notna()
        valid_delta_val = data['Amount_Delta_Value'] >= -1
        valid_delta_pct = data['Amount_Delta_Percentage'] <= 90
        
        # Approved logic
        approved_mask = has_invoice & valid_delta_val & valid_delta_pct
        data.loc[approved_mask, 'Auto_Validation_Status'] = 'Approved'
        
        # Disapproved logic
        disapproved_mask = has_invoice & (~valid_delta_val | ~valid_delta_pct)
        data.loc[disapproved_mask, 'Auto_Validation_Status'] = 'Disapproved'

        # Low cost & missing invoice logic
        is_missing_or_zero_invoice = (
            data['Invoice_Number'].isna() | 
            (data['Invoice_Number'] == '0') | 
            (data['Invoice_Number'] == 0)
        )
        low_cost_mask = (data['Amount_BQ'] <= 5) & is_missing_or_zero_invoice
        data.loc[low_cost_mask, 'Auto_Validation_Status'] = 'Approved'

        # Missing Invoice logic
        missing_invoice_mask = data['Invoice_Number'].isna() & ~low_cost_mask
        data.loc[missing_invoice_mask, 'Auto_Validation_Status'] = 'Missing Invoice'

        # Cleanup
        data = data.replace([np.inf, -np.inf], 0)
        data.columns = data.columns.str.lower()
        
        return data
    
    def save_data(self, data, table_id):
        """
        Save data to BigQuery.
        """
        self.bigq_handler.append_data(data, table_id)
