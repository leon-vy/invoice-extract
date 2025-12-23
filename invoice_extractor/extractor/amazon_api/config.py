"""
Configuration et constantes pour l'extraction des factures Amazon Ads.
"""
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Charger le .env (à la racine du projet)
load_dotenv()

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
