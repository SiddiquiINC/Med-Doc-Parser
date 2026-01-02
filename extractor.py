"""Extraction logic using LLM and regex fallback."""

import json
import logging
import re
from typing import Dict, Any, List, Optional

import requests

from app.config import config
from app.utils import parse_date_to_iso

logger = logging.getLogger(__name__)


EXTRACTION_PROMPT_TEMPLATE = """You are a strict extractor. Input is OCR text with page separators like ===PAGE:1===.

Return EXACTLY one JSON object (nothing else) with:
- doctor_name (string or "")
- patient_name (string or "")
- dob (YYYY-MM-DD or "")
- confidence {{"doctor":0-1,"patient":0-1,"dob":0-1}}
- evidence [ "PAGE:1:snippet" ]

Example:
OCR: "===PAGE:1=== Patient Name: Jane Doe DOB: 02/14/1980"
JSON: {{"doctor_name":"","patient_name":"Jane Doe","dob":"1980-02-14","confidence":{{"doctor":0,"patient":0.95,"dob":0.9}},"evidence":["PAGE:1:Patient Name: Jane Doe","PAGE:1:DOB: 02/14/1980"]}}

Now extract from:
{ocr_text}
"""


def build_prompt(pages: List[Dict[str, str]]) -> str:
    """
    Build extraction prompt from OCR pages.
    
    Args:
        pages: List of page dicts with 'page' and 'text' keys
        
    Returns:
        Formatted prompt string
    """
    # Combine pages with separators
    ocr_parts = []
    max_chars = 8000  # Limit total prompt length
    current_chars = 0
    
    for page_data in pages:
        page_num = page_data["page"]
        text = page_data["text"]
        
        separator = f"===PAGE:{page_num}===\n"
        page_content = separator + text + "\n"
        
        if current_chars + len(page_content) > max_chars:
            # Truncate to fit
            remaining = max_chars - current_chars
            if remaining > len(separator):
                page_content = separator + text[:remaining - len(separator)] + "...[truncated]\n"
            else:
                break
        
        ocr_parts.append(page_content)
        current_chars += len(page_content)
    
    ocr_text = "".join(ocr_parts)
    return EXTRACTION_PROMPT_TEMPLATE.format(ocr_text=ocr_text)


def call_ollama(prompt: str) -> Dict[str, Any]:
    """
    Call local Ollama API for structured extraction.
    
    Args:
        prompt: Extraction prompt
        
    Returns:
        Parsed JSON response or empty dict on failure
    """
    try:
        payload = {
            "model": config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        logger.info("Calling Ollama at %s with model %s", config.OLLAMA_URL, config.OLLAMA_MODEL)
        
        response = requests.post(
            config.OLLAMA_URL,
            json=payload,
            timeout=config.OLLAMA_TIMEOUT
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Extract response text
        if "response" in data:
            response_text = data["response"]
        elif "text" in data:
            response_text = data["text"]
        else:
            logger.error("Unexpected Ollama response format: %s", list(data.keys()))
            return {}
        
        # Try to parse as JSON
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from text (handle cases with preamble)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
            
            logger.warning("Failed to parse Ollama response as JSON")
            return {}
    
    except requests.exceptions.RequestException as e:
        logger.error("Ollama request failed: %s", str(e))
        return {}
    except Exception as e:
        logger.error("Unexpected error calling Ollama: %s", str(e))
        return {}


def regex_fallback(full_text: str) -> Dict[str, Any]:
    """
    Fallback extraction using regex patterns.
    
    Args:
        full_text: Combined OCR text from all pages
        
    Returns:
        Extraction result dict
    """
    result = {
        "doctor_name": "",
        "patient_name": "",
        "dob": "",
        "confidence": {"doctor": 0.0, "patient": 0.0, "dob": 0.0},
        "evidence": []
    }
    
    # Patient name patterns
    patient_patterns = [
        r"Patient\s*Name\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        r"Patient\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        r"Name\s*of\s*Patient\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
    ]
    
    for pattern in patient_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            result["patient_name"] = match.group(1).strip()
            result["confidence"]["patient"] = 0.6
            result["evidence"].append(f"REGEX:Patient pattern matched: {match.group(0)[:50]}")
            break
    
    # Doctor name patterns
    doctor_patterns = [
        r"Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"Doctor\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        r"Physician\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        r"Signature\s*[:\-]?\s*Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
    ]
    
    for pattern in doctor_patterns:
        match = re.search(pattern, full_text)
        if match:
            result["doctor_name"] = "Dr. " + match.group(1).strip()
            result["confidence"]["doctor"] = 0.5
            result["evidence"].append(f"REGEX:Doctor pattern matched: {match.group(0)[:50]}")
            break
    
    # DOB patterns
    dob_patterns = [
        r"(?:DOB|Date\s+of\s+Birth)\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        r"(?:DOB|Date\s+of\s+Birth)\s*[:\-]?\s*(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})",
        r"Born\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
    ]
    
    for pattern in dob_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            iso_date = parse_date_to_iso(date_str)
            if iso_date:
                result["dob"] = iso_date
                result["confidence"]["dob"] = 0.65
                result["evidence"].append(f"REGEX:DOB pattern matched: {match.group(0)[:50]}")
                break
    
    return result


def combine(pages: List[Dict]) -> Dict[str, Any]:
    """
    Orchestrate LLM call and regex fallback to extract fields.
    
    Args:
        pages: List of page dicts with OCR text
        
    Returns:
        Final extraction result with all fields
    """
    # Build full text for fallback
    full_text = "\n".join(p.get("text", "") for p in pages)
    
    # Try LLM extraction first
    prompt = build_prompt(pages)
    llm_result = call_ollama(prompt)
    
    llm_failed = not llm_result or not isinstance(llm_result, dict)
    
    if llm_failed:
        logger.info("LLM extraction failed, using regex fallback")
        result = regex_fallback(full_text)
        result["_llm_unavailable"] = True
    else:
        # Validate and normalize LLM result
        result = {
            "doctor_name": llm_result.get("doctor_name", ""),
            "patient_name": llm_result.get("patient_name", ""),
            "dob": llm_result.get("dob", ""),
            "confidence": llm_result.get("confidence", {"doctor": 0.0, "patient": 0.0, "dob": 0.0}),
            "evidence": llm_result.get("evidence", [])
        }
        
        # Normalize DOB to ISO format
        if result["dob"]:
            iso_date = parse_date_to_iso(result["dob"])
            if iso_date:
                result["dob"] = iso_date
            else:
                result["dob"] = ""
                result["confidence"]["dob"] = 0.0
        
        # Fallback for empty fields using regex
        regex_result = regex_fallback(full_text)
        
        if not result["patient_name"] and regex_result["patient_name"]:
            result["patient_name"] = regex_result["patient_name"]
            result["confidence"]["patient"] = regex_result["confidence"]["patient"]
            result["evidence"].extend(regex_result["evidence"])
        
        if not result["doctor_name"] and regex_result["doctor_name"]:
            result["doctor_name"] = regex_result["doctor_name"]
            result["confidence"]["doctor"] = regex_result["confidence"]["doctor"]
            result["evidence"].extend(regex_result["evidence"])
        
        if not result["dob"] and regex_result["dob"]:
            result["dob"] = regex_result["dob"]
            result["confidence"]["dob"] = regex_result["confidence"]["dob"]
            result["evidence"].extend(regex_result["evidence"])
    
    # Determine if manual review needed
    conf = result.get("confidence", {})
    flag_for_review = (
        conf.get("doctor", 0.0) < config.CONF_THRESHOLD or
        conf.get("patient", 0.0) < config.CONF_THRESHOLD or
        conf.get("dob", 0.0) < config.CONF_THRESHOLD or
        result.get("_llm_unavailable", False)
    )
    
    result["flag_for_review"] = flag_for_review
    
    return result
