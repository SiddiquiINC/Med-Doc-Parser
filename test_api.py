"""Tests for FastAPI endpoints."""

import io
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_test_image_bytes() -> bytes:
    """Create test image as bytes."""
    img = Image.new("RGB", (400, 200), color="white")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_parse_endpoint_success(monkeypatch):
    """Test successful document parsing."""
    def mock_pdf_bytes_to_pages(file_bytes, dpi=None):
        return [{"page": 1, "text": "Patient Name: John Doe\nDOB: 02/14/1980"}]
    
    def mock_combine(pages):
        return {
            "doctor_name": "Dr. Alice Smith",
            "patient_name": "John Doe",
            "dob": "1980-02-14",
            "confidence": {"doctor": 0.9, "patient": 0.97, "dob": 0.95},
            "evidence": ["PAGE:1:Patient: John Doe"],
            "flag_for_review": False
        }
    
    monkeypatch.setattr("app.main.pdf_bytes_to_pages", mock_pdf_bytes_to_pages)
    monkeypatch.setattr("app.main.combine", mock_combine)
    
    img_bytes = create_test_image_bytes()
    response = client.post(
        "/parse",
        files={"file": ("test.png", img_bytes, "image/png")}
    )
    
    assert response.status_code == 200
    body = response.json()
    assert body["patient_name"] == "John Doe"
    assert body["flag_for_review"] is False


def test_parse_endpoint_empty_file():
    """Test parsing with empty file."""
    response = client.post(
        "/parse",
        files={"file": ("test.png", b"", "image/png")}
    )
    
    assert response.status_code == 400
