"""OCR functionality for medical document parsing."""

import io
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any

import pytesseract
from PIL import Image, ImageEnhance, ImageOps
from pdf2image import convert_from_path

from app.config import config
from app.utils import normalize_text

logger = logging.getLogger(__name__)


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Preprocess image for better OCR results.
    
    Args:
        image: PIL Image object
        
    Returns:
        Preprocessed PIL Image
    """
    # Convert to grayscale
    if image.mode != "L":
        image = ImageOps.grayscale(image)
    
    # Apply autocontrast
    image = ImageOps.autocontrast(image)
    
    # Optional: enhance sharpness slightly
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.5)
    
    return image


def extract_text_from_image(image: Image.Image) -> str:
    """
    Extract text from a single image using Tesseract OCR.
    
    Args:
        image: PIL Image object
        
    Returns:
        Extracted text string
    """
    try:
        preprocessed = preprocess_image(image)
        text = pytesseract.image_to_string(preprocessed, lang="eng")
        return normalize_text(text)
    except Exception as e:
        logger.error("OCR extraction failed: %s", str(e))
        return ""


def pdf_bytes_to_pages(file_bytes: bytes, dpi: int = None) -> List[Dict[str, Any]]:
    """
    Convert PDF bytes or image bytes to list of page dictionaries with OCR text.
    
    Args:
        file_bytes: Raw file bytes (PDF or image)
        dpi: DPI for PDF rendering (default from config)
        
    Returns:
        List of dicts with keys: page (int), text (str)
    """
    if dpi is None:
        dpi = config.OCR_DPI
    
    pages = []
    
    try:
        # Try to open as image first
        image = Image.open(io.BytesIO(file_bytes))
        text = extract_text_from_image(image)
        pages.append({"page": 1, "text": text})
        logger.info("Processed single image, extracted %d characters", len(text))
        return pages
    except Exception:
        # Not an image, try as PDF
        pass
    
    # Process as PDF
    temp_dir = config.PROCESSING_TEMP_DIR or tempfile.gettempdir()
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir=temp_dir) as tmp_file:
        tmp_path = Path(tmp_file.name)
        try:
            tmp_file.write(file_bytes)
            tmp_file.flush()
            
            # Convert PDF to images
            images = convert_from_path(str(tmp_path), dpi=dpi)
            logger.info("Converted PDF to %d images at %d DPI", len(images), dpi)
            
            # Limit processing for large documents
            max_pages = config.MAX_PAGES_PROCESS
            if len(images) > max_pages:
                # Take header and footer pages
                header_count = config.HEADER_PAGES
                footer_count = config.FOOTER_PAGES
                selected_images = images[:header_count] + images[-footer_count:]
                logger.info("Document has %d pages, processing first %d and last %d", 
                          len(images), header_count, footer_count)
                
                # Process selected pages
                for idx, img in enumerate(selected_images):
                    # Map to actual page numbers
                    if idx < header_count:
                        page_num = idx + 1
                    else:
                        page_num = len(images) - footer_count + (idx - header_count) + 1
                    
                    text = extract_text_from_image(img)
                    pages.append({"page": page_num, "text": text})
            else:
                # Process all pages
                for idx, img in enumerate(images):
                    text = extract_text_from_image(img)
                    pages.append({"page": idx + 1, "text": text})
            
            total_chars = sum(len(p["text"]) for p in pages)
            logger.info("Parsed %d pages, total_chars=%d", len(pages), total_chars)
            
        finally:
            # Clean up temp file
            try:
                tmp_path.unlink()
            except Exception as e:
                logger.warning("Failed to delete temp file %s: %s", tmp_path, e)
    
    return pages
