import logging
import time
from invoice_extractor.core import ProcessorRegistry, settings

# Import processors to trigger registration
from invoice_extractor.extractor.sa.sa_processor import SAProcessor
from invoice_extractor.extractor.amazon_api.adsp_processor import ADSPProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_extraction():
    logger.info("Starting extraction process for all platforms...")
    
    platforms = ProcessorRegistry.list_platforms()
    logger.info(f"Registered platforms: {platforms}")
    
    for platform in platforms:
        try:
            logger.info(f"Running extractor for {platform}...")
            processor = ProcessorRegistry.get_processor(platform)
            
            if platform == "SA":
                processor.run(
                    invoices_path=str(settings.invoices_path), 
                    output_temp_path=str(settings.output_temp)
                )
            elif platform == "ADSP":
                processor.run(
                    start_date=settings.start_date, 
                    end_date=settings.end_date, 
                    regions=settings.regions
                )
            # Add other platforms as they are implemented
            
            logger.info(f"Successfully finished extraction for {platform}")
            time.sleep(5) # Avoid rate limits/concurrency issues
            
        except Exception as e:
            logger.error(f"Error during extraction for {platform}: {e}", exc_info=True)

if __name__ == "__main__":
    run_extraction()