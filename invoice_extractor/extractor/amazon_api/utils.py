from datetime import datetime
import pandas as pd

from invoice_extractor.extractor.amazon_api.config import logger

def is_date_in_range(invoice_date_str: str, start_date: str, end_date: str) -> bool:

    if not invoice_date_str:
        return False

    try:
        date_str = str(invoice_date_str).strip()
        date_part = date_str.split("T")[0].split(" ")[0]

        date_formats = [
            "%Y-%m-%d",  
            "%Y%m%d", 
        ]

        invoice_date = None
        for fmt in date_formats:
            try:
                invoice_date = datetime.strptime(date_part, fmt).date()
                break
            except ValueError:
                continue

        if invoice_date is None:
            logger.warning(f"Format de date non reconnu: '{invoice_date_str}'")
            return False

        start_date_obj = None
        end_date_obj = None
        for fmt in date_formats:
            try:
                start_date_obj = datetime.strptime(str(start_date).strip(), fmt).date()
                break
            except ValueError:
                continue
        for fmt in date_formats:
            try:
                end_date_obj = datetime.strptime(str(end_date).strip(), fmt).date()
                break
            except ValueError:
                continue

        if start_date_obj is None or end_date_obj is None:
            logger.warning(f"Impossible de parser start_date ou end_date: {start_date}, {end_date}")
            return False

        return start_date_obj <= invoice_date <= end_date_obj
    except (ValueError, AttributeError) as e:
        logger.warning(f"Impossible de parser la date '{invoice_date_str}': {e}")
        return False

def format_date_to_iso(date_str: str) -> str:
    """
    Convertit une date en format ISO date seulement (YYYY-MM-DD)
    Gère les formats: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, YYYYMMDD
    Retourne seulement la date sans heure, minutes, secondes
    """
    if not date_str:
        return None
    
    try:
        date_str = str(date_str).strip()
        date_part = date_str.split("T")[0].split(" ")[0]
        
        date_formats = [
            "%Y-%m-%d",  
            "%Y%m%d",
        ]
        
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_part, fmt).date()
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        logger.warning(f"Format de date non reconnu dans format_date_to_iso: '{date_str}'")
        return None
    except (ValueError, AttributeError) as e:
        logger.warning(f"Impossible de parser la date '{date_str}' dans format_date_to_iso: {e}")
        return None

def transform(json_data: dict, region: str, profile_id: str, account_name: str) -> pd.DataFrame:

    try:
        payload = json_data.get("payload", {})
        invoice_summary = payload.get("invoiceSummary", {})
        invoice_lines = payload.get("invoiceLines", [])

        if not invoice_summary:
            logger.warning("Aucun invoiceSummary trouvé dans les données JSON")
            return pd.DataFrame()

        # Données de base de la facture
        base_data = {
            "region": region,
            "profile_id": profile_id,
            "account_name": account_name,
            "invoice_number": invoice_summary.get("id"),
            "status": invoice_summary.get("status"),
            "from_date": invoice_summary.get("fromDate"),
            "to_date": invoice_summary.get("toDate"),
            "invoice_date": format_date_to_iso(invoice_summary.get("invoiceDate")),
            "due_date": invoice_summary.get("dueDate"),
            "total_amount_factured": invoice_summary.get("amountDue", {}).get("amount"),
            "currency_code": invoice_summary.get("amountDue", {}).get("currencyCode"),
            "vate_rate": invoice_summary.get("taxRate"),
        }

        if not invoice_lines:
            return pd.DataFrame([base_data])

        total_supply = 0.0
        total_3party = 0.0
        total_platform = 0.0
        total_audience = 0.0
        total_reg = 0.0
        
        line_name = None
        campaign_id = None
        campaign_aid = None
        campaign_name = None

        # Calcul des montants agrégés
        for line in invoice_lines:
            if line_name is None:
                line_name = line.get("name")
            if campaign_id is None:
                campaign_id = line.get("campaignId")
            if campaign_aid is None:
                campaign_aid = line.get("campaignAID")
            if campaign_name is None:
                campaign_name = line.get("campaignName")
                
            supply_cost_val = line.get('supplyCost', {}).get('amount', 0.0)
            total_supply += supply_cost_val
            
            for fee in line.get('fees', []):
                amt = fee.get('cost', {}).get('amount', 0.0)
                f_type = fee.get('feeType')
                if f_type == 'PLATFORM_FEE': 
                    total_platform += amt
                elif f_type == 'AUDIENCE_FEE': 
                    total_audience += amt
                elif f_type in ['3P_AUTO_NON_ABSORBED_FEE', '3P_PREBID_FEE']: 
                    total_3party += amt
                elif f_type == 'REGULATORY_ADVERTISING_FEE': 
                    total_reg += amt

        subtotal_ht = total_supply + total_platform + total_audience + total_3party
        total_ttc = subtotal_ht + total_reg

        # Préparation de la ligne de données
        final_row = base_data.copy()
        final_row.update({
            "line_name": line_name,
            "campaign_id": campaign_id,
            "campaign_aid": campaign_aid,
            "campaign_name": campaign_name,
            "supply_cost": round(total_supply, 2),
            "platform_fees": round(total_platform, 2),
            "audience_fees": round(total_audience, 2),
            "subtotal_ht": round(subtotal_ht, 2),
            "3party_fees": round(total_3party, 2),
            "regulatory_fees": round(total_reg, 2),
            "total_ttc": round(total_ttc, 2)
        })

        df = pd.DataFrame([final_row])
        logger.info(f"DataFrame créé avec {len(df)} ligne(s) pour la facture {base_data['invoice_number']}")
        return df

    except Exception as e:
        logger.error(f"Erreur lors de la transformation JSON vers DataFrame: {e}")
        return pd.DataFrame()