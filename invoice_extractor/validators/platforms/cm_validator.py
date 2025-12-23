import sys
from pathlib import Path

# Add project root to sys.path to allow imports
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from invoice_extractor.validators.core.base_validator import BaseApproval
import numpy as np
import pandas as pd

class CMApproval(BaseApproval):
    def __init__(self, service_account, query_bigq, query_provider, dataset_id):
        super().__init__(service_account, query_bigq, query_provider, dataset_id)
    
    def clean_invoice_numbers(invoice_string):
        # Split by comma to get each part
        invoices = [inv.strip() for inv in invoice_string.split(',')]
        invoices = [inv for inv in invoices if inv != 'No Invoice' and inv != '']
        
        if invoices:
            return ', '.join(invoices)
        else:
            return ''

    def get_invoice_number(group):
        invoice_nums = group['invoice_number'].dropna().unique()
        if len(invoice_nums) == 0:
            return np.nan
        
        return str(invoice_nums[0]) if not pd.isna(invoice_nums[0]) else np.nan
    
    def cleaning_data(self, month_bigq, month_provider):

        df_provider = self.fetch_bigq_data(month_bigq)
        df_bgq = self.fetch_provider_data(month_provider)

        df_provider['CPC'] = pd.to_numeric(df_provider['CPC'], errors='coerce')
        df_provider['CPM'] = pd.to_numeric(df_provider['CPM'], errors='coerce')

        df_provider.rename(columns={
            "advertiser_id": "advertiserId",
            "uom": "types",
            "unit_price": "Fee",
        }, inplace=True)

        grouped_df_bgq = df_bgq.groupby(['Month','Partner','advertiserId','Advertiser','types', 'Fee'], as_index=False)['impressions_clicks'].sum()
        grouped_df_provider = df_provider.groupby(['invoice_number','vat','advertiser_name', 'advertiserId', 'types', 'Fee'], as_index=False)['quantity'].sum()

        grouped_df_provider['invoice_number'] = grouped_df_provider['invoice_number'].astype(str)

        merged_df = grouped_df_bgq.merge(
            grouped_df_provider[['invoice_number','advertiserId', 'types', 'Fee', 'quantity']],  # Include 'unit_price'
            on=['advertiserId', 'types', 'Fee'],
            how='outer'
        )
        merged_df.rename(columns={
            "impressions_clicks":"Impr_BQ",
            "quantity": "Impr_Inv",
        }, inplace=True)

        merged_df["Click_amount_BQ"] = np.where(
            merged_df["types"] == "CPC",
            merged_df["Fee"] * merged_df["Impr_BQ"],
            0
        )

        merged_df["Impr_amount_BQ"] = np.where(
            merged_df["types"] == "CPC",
            0,
            (merged_df["Fee"] * merged_df["Impr_BQ"]) / 1000
        )

        merged_df["Click_amount_Inv"] = np.where(
            merged_df["types"] == "CPC",
            merged_df["Fee"] * merged_df["Impr_Inv"],
            0
        )

        merged_df["Impr_amount_Inv"] = np.where(
            merged_df["types"] == "CPC",
            0,
            (merged_df["Fee"] * merged_df["Impr_Inv"]) / 1000
        )

        # Aggregate metrics by Partner and type
        aggregated_df = merged_df.groupby(['Month', 'Partner', 'types']).agg(
            Impr_BQ=('Impr_BQ', 'sum'),
            Impr_Inv=('Impr_Inv', 'sum'),
            Click_amount_BQ=('Click_amount_BQ', 'sum'),
            Impr_amount_BQ=('Impr_amount_BQ', 'sum'),
            Click_amount_Inv=('Click_amount_Inv', 'sum'),
            Impr_amount_Inv=('Impr_amount_Inv', 'sum')
        ).reset_index()

        # Pivot the aggregated data to get separate columns for CPC and CPM
        result_bq = aggregated_df.pivot_table(
            index=['Month', 'Partner'],
            columns='types',
            values=[
                'Impr_BQ', 'Impr_Inv',
                'Click_amount_BQ', 'Impr_amount_BQ',
                'Click_amount_Inv', 'Impr_amount_Inv'
            ],
            aggfunc='sum'
        ).reset_index()

        # Flatten multi-level columns
        result_bq.columns = ['_'.join(col).strip() if col[1] else col[0] for col in result_bq.columns.values]

        # Rename columns to match the original output structure
        result_bq.rename(columns={
            "Impr_BQ_CPC": "Clicks_BQ",
            "Impr_Inv_CPC": "Clicks_Inv",
            "Impr_BQ_CPM": "Impr_BQ",
            "Impr_Inv_CPM": "Impr_Inv",
            "Click_amount_BQ_CPC": "Click_Amount_BQ",
            "Impr_amount_BQ_CPM": "Impr_Amount_BQ",
            "Click_amount_Inv_CPC": "Click_Amount_Inv",
            "Impr_amount_Inv_CPM": "Impr_Amount_Inv",
        }, inplace=True)

        # Drop unnecessary columns that might have been created for CPM CPC amounts
        result_bq.drop(columns=[col for col in result_bq.columns if 'Impr_amount_BQ_CPC' in col or 'Click_amount_BQ_CPM' in col or 'Impr_amount_Inv_CPC' in col or 'Click_amount_Inv_CPM' in col], errors='ignore', inplace=True)

        # Calculate invoice numbers per partner
        invoice_numbers = merged_df.groupby(['Month','Partner']).apply(CMApproval.get_invoice_number).reset_index()
        invoice_numbers.columns = ['Month','Partner', 'invoice_number']

        # Merge invoice numbers
        result_bq = result_bq.merge(invoice_numbers, on=['Month', 'Partner'], how="left")

        result_bq.fillna(0, inplace=True)

        result_bq["Click_Amount_BQ"] = result_bq["Click_Amount_BQ"].round(2)
        result_bq["Impr_Amount_BQ"] = result_bq["Impr_Amount_BQ"].round(2)
        result_bq["Click_Amount_Inv"] = result_bq["Click_Amount_Inv"].round(2)
        result_bq["Impr_Amount_Inv"] = result_bq["Impr_Amount_Inv"].round(2)

        result_bq["Amount_BQ"] = result_bq["Click_Amount_BQ"] + result_bq["Impr_Amount_BQ"]
        result_bq["Amount_Inv"] = result_bq["Click_Amount_Inv"] + result_bq["Impr_Amount_Inv"]

        return result_bq
