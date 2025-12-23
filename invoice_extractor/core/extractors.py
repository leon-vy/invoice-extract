from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import List, Optional, Any
import logging
import pandas as pd
import time

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-generativeai not installed. Gemini fallback will not be available.")

from invoice_extractor.utils.extractor_utils import (
    encode_image,
    extract_text_from_pdf,
    convert_pdf_to_images,
    get_pdf_files,
    cleanup_temp_images
)

class BaseInvoiceDataOutput(BaseModel):
    """Base model for all invoices"""
    invoice_number: str = Field(description="Exact invoice number")
    billing_period: str = Field(description="Billing period in YYYY-MM-DD format")
    
    class Config:
        extra = "forbid"

class BaseInvoiceExtractor(ABC):
    """Abstract base class for all extractors (AI-based or otherwise)"""
    
    def __init__(self, openai_client: Any, model: str = "gpt-4o", prompt: str = "", output_model: BaseModel = None):
        self.model = model
        self.client = openai_client
        self.output_model = output_model
        self.base_prompt = prompt 
    
    def process_invoice_openai_vision(self, pdf_path: str, output_dir: str) -> Optional[BaseInvoiceDataOutput]:
        """Process a single invoice using OpenAI Vision API"""
        images = []
        try:
            text = extract_text_from_pdf(pdf_path)
            images = convert_pdf_to_images(pdf_path, output_dir)
            
            content = [{"type": "text", "text": self.base_prompt.format(extracted_text=text, images=len(images))}]
            
            for img_path in images:
                base64_image = encode_image(img_path)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                })
            
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                response_format=self.output_model
            )
            
            return completion.choices[0].message.parsed 
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}", exc_info=True)
            return None
        finally:
            cleanup_temp_images(images)
    
    def process_invoice_gemini_vision(self, pdf_path: str, output_dir: str) -> Optional[BaseInvoiceDataOutput]:
        """Process a single invoice using Gemini Vision API fallback"""
        if not GENAI_AVAILABLE:
            logger.warning("Gemini not available. Install google-generativeai to use this feature.")
            return None
        
        images = []
        try:
            text = extract_text_from_pdf(pdf_path)
            images = convert_pdf_to_images(pdf_path, output_dir)

            content = [{"type": "text", "text": self.base_prompt.format(extracted_text=text, images=len(images))}]
            
            for img_path in images:
                base64_image = encode_image(img_path)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                })
            
            response = genai.GenerativeModel(self.model).generate_content(content)
            
            return response.text 
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}", exc_info=True)
            return None
        finally:
            cleanup_temp_images(images)
    
    def process_batch(self, pdf_dir: str, output_dir: str, 
                     batch_size: int = 10, pause_seconds: int = 30) -> List[Any]:
        """Process PDFs in batches"""
        pdf_files = get_pdf_files(pdf_dir)
        results = []
        
        for i in range(0, len(pdf_files), batch_size):
            batch = pdf_files[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} files)")
            
            for pdf_file in batch:
                logger.info(f"Processing {pdf_file}")
                result = self.process_invoice_openai_vision(str(pdf_file), output_dir)
                if not result:
                    logger.warning(f"OpenAI processing failed for {pdf_file}, falling back to Gemini")
                    result = self.process_invoice_gemini_vision(str(pdf_file), output_dir)
                    if result:
                        logger.info(f"Gemini fallback successful for {pdf_file}")
                    else:
                        logger.error(f"Both OpenAI and Gemini processing failed for {pdf_file}")
                if result:
                    results.append(result)
            
            if i + batch_size < len(pdf_files):
                logger.info(f"Pausing for {pause_seconds} seconds...")
                time.sleep(pause_seconds)
        
        return results

    @abstractmethod
    def process_data(self, invoices: List[Any]) -> pd.DataFrame:
        """Process extracted data into a specific format for the platform"""
        pass
