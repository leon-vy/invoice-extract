from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import List, Optional
import os

class Settings(BaseSettings):
    # API Keys
    api_key_openai: str = os.getenv("API_KEY_OPENAI", "")
    
    # Paths
    project_root: Path = Path(__file__).parent.parent  # Points to invoice_extractor/
    service_account_pads: Path = project_root / "service_account_pads.json"
    service_account_provider: Path = project_root / "service-account.json"
    invoices_path: Path = project_root / "data" / "invoices"
    output_temp: Path = project_root / "data" / "temp"
    
    # BigQuery
    dataset_id_pads: str = "fact_pads"
    
    # Processing
    regions: List[str] = ["US", "EU"]
    
    # Default Dates
    @property
    def start_date(self) -> str:
        from datetime import datetime
        return datetime.now().replace(day=1).strftime("%Y-%m-%d")
    
    @property
    def end_date(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

TYPE_MAP = {
    'int64': 'INTEGER',
    'int32': 'INTEGER',
    'float64': 'FLOAT',
    'float32': 'FLOAT',
    'bool': 'BOOLEAN',
    'datetime64[ns]': 'TIMESTAMP',
    'object': 'STRING',
}
