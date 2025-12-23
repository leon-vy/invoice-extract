from typing import List, Any
from pathlib import Path
import base64
import os
import logging

from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError
import pdfplumber

logger = logging.getLogger(__name__)


def encode_image(image_path: str) -> str:
    """Encode image to base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using pdfplumber"""
    text_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text_data.append(extracted_text)
    return "\n".join(text_data)


def convert_pdf_to_images(pdf_path: str, output_dir: str) -> List[str]:
    """Convert PDF to images"""
    try:
        images = convert_from_path(pdf_path, dpi=300)  # augmenter la qualité des images
    except PDFInfoNotInstalledError:
        error_msg = "pdf2image n'est pas installé. Veuillez installer la bibliothèque pdf2image."
        raise RuntimeError(error_msg)
    
    image_paths = []
    
    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    for i, image in enumerate(images):
        image_path = f"{output_dir}/temp_page_{i+1}.jpg"
        image.save(image_path, "JPEG")
        image_paths.append(image_path)
    
    return image_paths


def get_pdf_files(pdf_dir: str) -> List[Path]:
    """Get all PDF files from directory"""
    pdf_files = []
    for pattern in ('*.PDF', '*.pdf'):
        pdf_files.extend(Path(pdf_dir).rglob(pattern))
    return pdf_files


def convert_float(var: Any, currency_symbols: List[str] = None) -> float:
    """Convert a value to float, removing currency symbols and formatting"""
    if var is None:
        return 0.00
    try:
        value = str(var)
        symbols_to_remove = currency_symbols or [' EUR', '€', ',', '%']
        for symbol in symbols_to_remove:
            value = value.replace(symbol, '')
        value = value.strip()
        return float(value) if value else 0.00
    except (ValueError, TypeError):
        return 0.00


def cleanup_temp_images(image_paths: List[str]) -> None:
    """Clean up temporary image files"""
    for img_path in image_paths:
        try:
            if os.path.exists(img_path):
                os.remove(img_path)
        except OSError as e:
            logger.warning(f"Could not remove temporary image {img_path}: {e}")

