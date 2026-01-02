"""FastAPI application for medical document parsing."""

import logging
from typing import Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from app.ocr import pdf_bytes_to_pages
from app.extractor import combine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Medical Document Parser",
    description="Microservice for extracting structured data from medical documents",
    version="1.0.0"
)


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Status dictionary
    """
    return {"status": "ok"}


@app.post("/parse")
async def parse_document(file: UploadFile = File(...)) -> JSONResponse:
    """
    Parse uploaded medical document and extract structured fields.
    
    Args:
        file: Uploaded PDF or image file
        
    Returns:
        JSON response with extracted fields:
        - doctor_name: str
        - patient_name: str
        - dob: str (ISO YYYY-MM-DD)
        - confidence: dict with per-field confidence scores
        - evidence: list of extraction evidence
        - flag_for_review: bool
    """
    try:
        # Validate file type
        content_type = file.content_type or ""
        allowed_types = [
            "application/pdf",
            "image/png",
            "image/jpeg",
            "image/jpg",
            "image/tiff",
            "image/bmp"
        ]
        
        if not any(allowed in content_type for allowed in allowed_types):
            # Also check filename
            if file.filename:
                ext = file.filename.lower().split(".")[-1]
                if ext not in ["pdf", "png", "jpg", "jpeg", "tiff", "tif", "bmp"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported file type: {content_type}. Allowed: PDF, PNG, JPEG, TIFF, BMP"
                    )
        
        logger.info("Processing upload: filename=%s, content_type=%s", 
                   file.filename or "unknown", content_type)
        
        # Read file bytes
        file_bytes = await file.read()
        logger.info("Read %d bytes from upload", len(file_bytes))
        
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        # OCR processing
        try:
            pages = pdf_bytes_to_pages(file_bytes)
        except Exception as e:
            logger.error("OCR processing failed: %s", str(e))
            raise HTTPException(
                status_code=422,
                detail=f"Failed to process document: {str(e)}"
            )
        
        if not pages:
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted from document"
            )
        
        # Extract structured data
        try:
            result = combine(pages)
        except Exception as e:
            logger.error("Extraction failed: %s", str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Extraction failed: {str(e)}"
            )
        
        # Clean up result for response
        response_data = {
            "doctor_name": result.get("doctor_name", ""),
            "patient_name": result.get("patient_name", ""),
            "dob": result.get("dob", ""),
            "confidence": result.get("confidence", {"doctor": 0.0, "patient": 0.0, "dob": 0.0}),
            "evidence": result.get("evidence", []),
            "flag_for_review": result.get("flag_for_review", True)
        }
        
        # Include LLM unavailable flag if present
        if result.get("_llm_unavailable"):
            response_data["_llm_unavailable"] = True
        
        logger.info("Extraction complete: flag_for_review=%s", response_data["flag_for_review"])
        
        return JSONResponse(content=response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in parse endpoint")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.exception_handler(503)
async def service_unavailable_handler(request, exc):
    """Handle service unavailable errors."""
    return JSONResponse(
        status_code=503,
        content={
            "error": "Service temporarily unavailable",
            "detail": "LLM service unreachable. Please retry later."
        }
    )
