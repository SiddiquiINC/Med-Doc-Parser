"""Configuration management for medical parser."""

import os
from typing import Optional


class Config:
    """Application configuration from environment variables."""
    
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma-3")
    OCR_DPI: int = int(os.getenv("OCR_DPI", "300"))
    CONF_THRESHOLD: float = float(os.getenv("CONF_THRESHOLD", "0.7"))
    PROCESSING_TEMP_DIR: Optional[str] = os.getenv("PROCESSING_TEMP_DIR")
    MAX_PAGES_PROCESS: int = int(os.getenv("MAX_PAGES_PROCESS", "50"))
    HEADER_PAGES: int = int(os.getenv("HEADER_PAGES", "5"))
    FOOTER_PAGES: int = int(os.getenv("FOOTER_PAGES", "3"))
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "30"))


config = Config()
