"""Utility functions for medical parser."""

import re
import unicodedata
from typing import Optional
from dateutil import parser as date_parser
from datetime import datetime


def normalize_text(text: str) -> str:
    """
    Normalize text by removing control characters and normalizing unicode.
    
    Args:
        text: Raw text string
        
    Returns:
        Normalized text string
    """
    # Remove control characters except newlines and tabs
    text = "".join(ch for ch in text if ch in ("\n", "\t") or not unicodedata.category(ch).startswith("C"))
    # Normalize unicode to NFKC form
    text = unicodedata.normalize("NFKC", text)
    return text


def parse_date_to_iso(date_str: str) -> Optional[str]:
    """
    Parse various date formats to ISO YYYY-MM-DD.
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        ISO formatted date string or None if parsing fails
    """
    if not date_str or not date_str.strip():
        return None
    
    try:
        # Try parsing with dateutil (handles many formats)
        parsed = date_parser.parse(date_str, fuzzy=True)
        # Validate reasonable DOB range (1900-current year)
        if 1900 <= parsed.year <= datetime.now().year:
            return parsed.strftime("%Y-%m-%d")
    except (ValueError, OverflowError):
        pass
    
    # Try common formats manually
    patterns = [
        r"(\d{4})-(\d{1,2})-(\d{1,2})",  # YYYY-MM-DD
        r"(\d{1,2})/(\d{1,2})/(\d{4})",  # MM/DD/YYYY
        r"(\d{1,2})-(\d{1,2})-(\d{4})",  # MM-DD-YYYY
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_str)
        if match:
            try:
                groups = match.groups()
                if len(groups[0]) == 4:  # YYYY first
                    year, month, day = groups
                else:  # MM/DD/YYYY
                    month, day, year = groups
                
                dt = datetime(int(year), int(month), int(day))
                if 1900 <= dt.year <= datetime.now().year:
                    return dt.strftime("%Y-%m-%d")
            except (ValueError, OverflowError):
                continue
    
    return None


def mask_phi(text: str, max_length: int = 100) -> str:
    """
    Mask PHI in text for logging purposes.
    
    Args:
        text: Text that may contain PHI
        max_length: Maximum length to return
        
    Returns:
        Masked version showing only length/stats
    """
    if not text:
        return "<empty>"
    return f"<text length={len(text)} chars, preview={text[:min(20, max_length)]}...>"
