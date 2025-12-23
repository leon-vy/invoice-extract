import sys
from pathlib import Path

# Add project root to sys.path to allow imports
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from invoice_extractor.validators.core.base_validator import BaseApproval

class SAApproval(BaseApproval):
    def __init__(self, service_account, query_bigq, query_provider, dataset_id):
        super().__init__(service_account, query_bigq, query_provider, dataset_id)
  
    def cleaning_data(self, month_bigq, month_provider):

        df_provider = self.fetch_bigq_data(month_bigq)
        df_bgq = self.fetch_provider_data(month_provider)
        
        df_bgq.rename(columns={
            "Accountid": "AccountID",
            "Media_cost": "Click_BQ",
            "Partner": "Partner_BQ",
            "Advertiser": "Advertiser_BQ",
            "Fee": "Fee_BQ"
        }, inplace=True)

        # Rename columns for consistency
        df_provider.rename(columns={
            "account_id": "AccountID",
            "quantity": "Click_Invoice",
            "invoice_number": "Invoice_Number"
        }, inplace=True)

        # Merge on 'Partner_id'
        merged_df = df_bgq.merge(df_provider[[
            'AccountID',
            'Click_Invoice',
            'Invoice_Number'
        ]], on='AccountID', how='outer')

        merged_df['Cost_BQ'] = (merged_df['Fee_BQ'] * merged_df['Click_BQ']).round(2)
        merged_df['Cost_Invoice'] = (merged_df['Fee_BQ'] * merged_df['Click_Invoice']).round(2)
        merged_df['Cost_Invoice'] = merged_df['Cost_Invoice'].fillna(0.0)

        return merged_df
