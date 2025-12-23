import logging
from datetime import datetime, timedelta
from invoice_extractor.core import settings
from invoice_extractor.validators.config.platform_config import PLATFORM_CONFIGS
from invoice_extractor.validators.platforms import (
    ADSPApproval, 
    CMApproval, 
    DVApproval, 
    SAApproval
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VALIDATOR_CLASSES = {
    "ADSP": ADSPApproval,
    "CM": CMApproval,
    "DV": DVApproval,
    "SA": SAApproval
}

def process_all_approvals(month_bigq: str, month_provider: str) -> dict:
    results = {}
    for platform_name, config in PLATFORM_CONFIGS.items():
        try:
            validator = VALIDATOR_CLASSES[platform_name](
                service_account=str(settings.service_account_pads),
                query_bigq=config["query_bigq"],
                query_provider=config["query_provider"],
                dataset_id=settings.dataset_id_pads
            )

            # 1. Cleaning & Merging Data
            logger.info(f"Fetching and cleaning data for {platform_name}...")
            cleaned_data = validator.cleaning_data(month_bigq, month_provider)
            
            # 2. Applying Business Rules
            logger.info(f"Applying rules for {platform_name}...")
            validated_data = validator.apply_rules(cleaned_data)
            
            # 3. Saving Data
            logger.info(f"Saving data for {platform_name}...")
            validator.save_data(validated_data, config["output_table"])
            
            results[platform_name] = "Success"
            logger.info(f"Successfully processed {platform_name}")

        except Exception as e:
            logger.error(f"Error processing {platform_name}: {e}")
            results[platform_name] = f"Failed: {str(e)}"
    
    return results


if __name__ == "__main__":
    today = datetime.now()
    first_day_current_month = today.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    first_day_previous_month = last_day_previous_month.replace(day=1)
    date_bigq = first_day_previous_month.strftime("%Y-%m-%d")

    date_provider = settings.start_date

    results = process_all_approvals(date_bigq, date_provider)
    
    print("\n" + "="*50)
    print("APPROVAL PROCESS RESULTS")
    print("="*50)
    for platform, result in results.items():
        print(f"{platform}: {result}")
    print("="*50)