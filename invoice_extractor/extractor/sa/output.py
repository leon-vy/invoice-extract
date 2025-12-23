from invoice_extractor.core import BaseInvoiceDataOutput
from typing import List
from pydantic import BaseModel, Field


class SAInvoiceLineItem(BaseModel):
    """Ligne d'une table de facture SA360"""
    description: str = Field(description="Description de la ligne")
    advertiser_name: str = Field(description="Nom de l'annonceur sur le tableau")
    account_id: str = Field(description="ID de l'annonceur")
    uom: str = Field(description="Unité de mesure")
    quantity: float = Field(description="Quantité")


class SAInvoiceDataOutput(BaseInvoiceDataOutput):
    """Structure complète d'une facture SA360"""

    invoice_number: str = Field(description="Numéro de la facture")
    billing_period: str = Field(description="Période de facturation")
    vat_rate: float = Field(description="Taux de TVA")
    
    rows: List[SAInvoiceLineItem] = Field(default_factory=list, description="Table principale")
