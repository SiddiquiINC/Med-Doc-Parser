"""Tests for extraction module."""

import json
import pytest
from unittest.mock import Mock

from app.extractor import build_prompt, call_ollama, regex_fallback, combine


def test_build_prompt():
    """Test prompt building from pages."""
    pages = [
        {"page": 1, "text": "Patient Name: John Doe"},
        {"page": 2, "text": "DOB: 02/14/1980"}
    ]
    
    prompt = build_prompt(pages)
    
    assert "===PAGE:1===" in prompt
    assert "===PAGE:2===" in prompt
    assert "Patient Name: John Doe" in prompt


def test_regex_fallback():
    """Test regex-based fallback extraction."""
    sample = """===PAGE:1===
    Medical Record
    Patient Name: John Q. Patient
    DOB: 02/14/1980
    
    Signature: Dr. Alice Smith
    """
    
    result = regex_fallback(sample)
    
    assert "John" in result["patient_name"]
    assert result["dob"] == "1980-02-14"
    assert "Dr." in result["doctor_name"]


def test_call_ollama_success(monkeypatch):
    """Test successful Ollama API call."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": json.dumps({
            "doctor_name": "Dr. Alice Smith",
            "patient_name": "John Doe",
            "dob": "1980-02-14",
            "confidence": {"doctor": 0.9, "patient": 0.97, "dob": 0.95},
            "evidence": ["PAGE:1:Patient: John Doe"]
        })
    }
    
    def mock_post(url, json=None, timeout=None):
        return mock_response
    
    monkeypatch.setattr("app.extractor.requests.post", mock_post)
    
    result = call_ollama("test prompt")
    
    assert result["doctor_name"] == "Dr. Alice Smith"
    assert result["patient_name"] == "John Doe"


def test_combine_with_llm_success(monkeypatch):
    """Test combine function with successful LLM extraction."""
    pages = [{"page": 1, "text": "Patient: John Doe\nDOB: 02/14/1980"}]
    
    def mock_call_ollama(prompt):
        return {
            "doctor_name": "Dr. Smith",
            "patient_name": "John Doe",
            "dob": "1980-02-14",
            "confidence": {"doctor": 0.9, "patient": 0.95, "dob": 0.9},
            "evidence": ["PAGE:1:Patient: John Doe"]
        }
    
    monkeypatch.setattr("app.extractor.call_ollama", mock_call_ollama)
    
    result = combine(pages)
    
    assert result["patient_name"] == "John Doe"
    assert result["doctor_name"] == "Dr. Smith"
    assert result["flag_for_review"] is False
