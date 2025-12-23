import sys
from pathlib import Path

import pandas as pd

# Add project root to sys.path to allow imports
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from invoice_extractor.validators.core.base_validator import BaseApproval

class ADSPApproval(BaseApproval):
    def __init__(self, service_account, query_bigq, query_provider,dataset_id):
        super().__init__(service_account, query_bigq, query_provider, dataset_id)
  
    def cleaning_data(self, month_bigq, month_provider):

        df_bgq = self.fetch_bigq_data(month_bigq)
        df_provider = self.fetch_provider_data(month_provider)
        

        merged_df = pd.merge(df_provider, df_bgq, on='campaign_id', how='outer')

        columns_numeric = ['supply_cost','platform_fees','audience_fees','subtotal_ht','3party_fees','regulatory_fees','total_ttc','Media_Cost','Platform_fee','Third_Party_Fee','Third_Party_Data_Services','Montant_amazon_by_pads']
        # Convert numeric columns to float, handling errors gracefully
        for col in columns_numeric:
            merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce')

        merged_df['amount_invoice'] = merged_df['subtotal_ht']+ merged_df['3party_fees']
        # merged_df.to_csv('merged_df.csv', index=False)

        merged_df['invoice_involved'] = merged_df.groupby('Advertiser')['invoice_number'].transform(
            lambda x: '.'.join(x.dropna().astype(str).unique()) if not x.dropna().empty else ''
        )

        grouped_result = merged_df.groupby('Advertiser').agg({
            'Media_Cost': 'sum',
            'Platform_fee': 'sum',
            'Third_Party_Fee': 'sum',
            'Third_Party_Data_Services': 'sum',
            'Montant_amazon_by_pads': 'sum',
            'amount_invoice': 'sum',
            'platform_fees': 'sum',
            'audience_fees': 'sum',
            '3party_fees': 'sum',
            'supply_cost': 'sum',
            'invoice_involved': 'first',
            'Product': 'first',
            'Month': 'first',
            'Partner': 'first',
        }).round(2).reset_index()

        grouped_result['Amount_Delta_Value'] = (grouped_result['Montant_amazon_by_pads'] - grouped_result['amount_invoice']).round(2)
        grouped_result['Amount_Delta_Percentage'] = grouped_result.apply(
            lambda row: round((row['Amount_Delta_Value']*100) / row['Montant_amazon_by_pads'], 2)
            if row['Montant_amazon_by_pads'] != 0 else 0, axis=1
        )
        mask = grouped_result['invoice_involved'].notna()
        grouped_result.loc[mask & (grouped_result['Amount_Delta_Value'] >= -1) & (grouped_result['Amount_Delta_Percentage'] <= 90), 'Auto_Validation_Status'] = 'Approved'
        grouped_result.loc[mask & ((grouped_result['Amount_Delta_Value'] < -1) | (grouped_result['Amount_Delta_Percentage'] > 90)), 'Auto_Validation_Status'] = 'Disapproved'

        # Cas où Amount_BQ < 5 et Invoice_Number est vide ou 0
        low_cost_missing_invoice_mask = (
            grouped_result['Montant_amazon_by_pads'] <= 5
            ) & (
                (grouped_result['invoice_involved'].isna()) | 
                (grouped_result['invoice_involved'] == '0') | 
                (grouped_result['invoice_involved'] == 0)
            )

        grouped_result.loc[low_cost_missing_invoice_mask, 'Auto_Validation_Status'] = 'Approved'

        # Cas où Invoice_Number est absent (NA)
        missing_invoice_mask = grouped_result['invoice_involved'].isna() & ~low_cost_missing_invoice_mask
        grouped_result.loc[missing_invoice_mask, 'Auto_Validation_Status'] = 'Missing Invoice'
        # Replace infinite values with 0
        grouped_result = grouped_result.replace([float('inf'), float('-inf')], 0)

        grouped_result.rename(columns={
            "Partner": "Partner_BQ",
            "Media_Cost": "Media_Cost_BQ",
            "Platform_fee": "Platform_Fee_BQ",
            "Third_Party_Fee": "Third_Party_Data_Fee_BQ",
            "Third_Party_Data_Services": "Third_Party_Data_Service_BQ",
            "Montant_amazon_by_pads": "Amount_BQ"
        }, inplace=True)
        
         
        return grouped_result
