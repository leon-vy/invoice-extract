import os
import time
from datetime import datetime

import requests

from invoice_extractor.extractor.amazon_api.config import logger
from invoice_extractor.extractor.amazon_api.utils import is_date_in_range

class AdspController:
    def __init__(self, region: str):
        self.region = region.upper()
        prefix = self.region

        self.client_id = os.getenv("CLIENT_ID_AMAZON")
        self.client_secret = os.getenv("SECRET_CLIENT_AMAZON")
        self.refresh_token = os.getenv("REFRESH_TOKEN_AMZ_API")
        self.api_url = os.getenv(f"API_{prefix}_URL_AMAZON")
        self.token_url = os.getenv(f"TOKEN_{prefix}_URL_AMAZON")

        if not all([self.client_id, self.client_secret, self.refresh_token, self.api_url, self.token_url]):
            raise ValueError(f"Variables manquantes pour {region} dans le .env")

        self.access_token = self._get_access_token()
        logger.info(f"Token obtenu pour {region}")

    def _get_access_token(self):
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }
        resp = requests.post(self.token_url, data=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _headers(self, profile_id: str = None):
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Amazon-Advertising-API-ClientId": self.client_id,
            "Content-Type": "application/json",
        }
        if profile_id:
            headers["Amazon-Advertising-API-Scope"] = str(profile_id)
        return headers

    def get_profiles(self):
        url = f"{self.api_url}/profiles"
        resp = requests.get(url, headers=self._headers(), timeout=60)
        resp.raise_for_status()
        return resp.json()
    
    def invoices_filter(self, profile_id: str, start_date: str, end_date: str):
        """Récupère les factures avec filtre sur invoiceDate (pas sur période de dépense)"""
        invoices = []
        cursor = None
        base_url = f"{self.api_url}/invoices"

        # Amazon accepte les filtres directement dans la query string
        params = {
            "invoiceDateStart": start_date,
            "invoiceDateEnd": end_date,
        }

        while True:
            url = base_url
            query_params = {**params}
            if cursor:
                query_params["cursor"] = cursor

            resp = requests.get(
                url, headers=self._headers(profile_id), params=query_params, timeout=60
            )
            resp.raise_for_status()
            payload = resp.json().get("payload", {})

            batch = payload.get("invoiceSummaries", [])
            for inv in batch:
                inv.update({"profileId": profile_id, "region": self.region})

            filtered_batch = []
            for inv in batch:
                invoice_date = inv.get("invoiceDate") or inv.get("date")
                if is_date_in_range(invoice_date, start_date, end_date):
                    filtered_batch.append(inv)
                else:
                    logger.debug(
                        f"Facture {inv.get('id')} exclue "
                        f"(date: {invoice_date} hors intervalle)"
                    )

            invoices.extend(filtered_batch)

            cursor = payload.get("nextCursor")
            if not cursor:
                break

        logger.info(
            f"[{self.region}] Profile {profile_id} → {len(invoices)} facture(s) "
            f"entre {start_date} et {end_date}"
        )
        return invoices

    def invoice_details(self, profile_id: str, invoice_id: str):
        url = f"{self.api_url}/invoices/{invoice_id}"
        resp = requests.get(url, headers=self._headers(profile_id), timeout=120)

        if resp.status_code == 429:
            logger.warning("Rate limit → pause 10s")
            time.sleep(10)
            return self.invoice_details(profile_id, invoice_id)

        resp.raise_for_status()
        return resp.json()
