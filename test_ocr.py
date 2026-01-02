"""Tests for OCR module."""

import pytest
from PIL import Image, ImageDraw
from io import BytesIO

from app.ocr import preprocess_image, extract_text_from_image, pdf_bytes_to_pages


def create_test_image(text: str = "Test Document") -> Image.Image:
    """Create a simple test image with text."""
    img = Image.new("RGB", (400, 200), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((50, 80), text, fill="black")
    return img


def test_preprocess_image():
    """Test image preprocessing."""
    img = create_test_image()
    processed = preprocess_image(img)
    
    assert processed is not None
    assert processed.mode == "L"  # Grayscale


def test_extract_text_from_image(monkeypatch):
    """Test text extraction with mocked pytesseract."""
    def mock_image_to_string(img, lang=None):
        return "Patient Name: John Doe\nDOB: 01/15/1980"
    
    monkeypatch.setattr("app.ocr.pytesseract.image_to_string", mock_image_to_string)
    
    img = create_test_image()
    text = extract_text_from_image(img)
    
    assert "Patient Name: John Doe" in text
    assert "DOB: 01/15/1980" in text


def test_pdf_bytes_to_pages_with_image(monkeypatch):
    """Test processing image bytes."""
    def mock_image_to_string(img, lang=None):
        return "Medical Record\nPatient: Jane Smith"
    
    monkeypatch.setattr("app.ocr.pytesseract.image_to_string", mock_image_to_string)
    
    img = create_test_image()
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes = img_bytes.getvalue()
    
    pages = pdf_bytes_to_pages(img_bytes)
    
    assert len(pages) == 1
    assert pages[0]["page"] == 1
    assert "Medical Record" in pages[0]["text"]


def test_pdf_bytes_to_pages_empty():
    """Test handling of empty/invalid bytes."""
    with pytest.raises(Exception):
        pdf_bytes_to_pages(b"")


def test_extract_text_error_handling(monkeypatch):
    """Test OCR error handling."""
    def mock_image_to_string_error(img, lang=None):
        raise RuntimeError("OCR failed")
    
    monkeypatch.setattr("app.ocr.pytesseract.image_to_string", mock_image_to_string_error)
    
    img = create_test_image()
    text = extract_text_from_image(img)
    
    assert text == ""
