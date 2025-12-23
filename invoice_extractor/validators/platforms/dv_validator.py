import sys
from pathlib import Path

# Add project root to sys.path to allow imports
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from invoice_extractor.validators.core.base_validator import BaseApproval

class DVApproval(BaseApproval):
    def __init__(self, service_account, query_bigq, query_provider, dataset_id):
        super().__init__(service_account, query_bigq, query_provider, dataset_id)
  
    def cleaning_data(self, month_bigq, month_provider):

        df_provider = self.fetch_bigq_data(month_bigq)
        df_bgq = self.fetch_provider_data(month_provider)
        
        df_provider.rename(columns={
            "partner_id": "PartnerID",
            "invoice_number": "Invoice_Number",
            "third_party": "3rd_Party_Data_Fee_Invoice",
            "total_cost": "Total_Cost_Invoice",
            "DTS_fees": "Regulatory_Fees_Invoice",
            }, 
            inplace=True
        )
        df_bgq.rename(columns={
            "Partner_id": "PartnerID", 
            "Partner": "Partner_BQ",
            "Media_cost": "Media_cost_BQ",
            "Platform_fee": "Platform_fee_BQ",
            "Third_Party_Data_Services": "3rd_Party_Data_Fee_BQ",
            "Regulatory_fee": "Regulatory_Fees_BQ",
            "Montant_total_facture_google_by_pads": "Amount_BQ",
            }, 
            inplace=True
        )
        merged_df = df_bgq.merge(df_provider[[
            'Invoice_Number',
            'PartnerID',
            '3rd_Party_Data_Fee_Invoice',
            'Total_Cost_Invoice',
            'Regulatory_Fees_Invoice',
            'Amount_Invoice'
        ]], on='PartnerID', how='outer')

        return merged_df
