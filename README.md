# Medical Document Parser

Production-ready microservice for extracting structured data from medical documents.

## Quick Start

### Install Dependencies

```bash
# 1. Install system dependencies
sudo apt-get install tesseract-ocr poppler-utils  # Ubuntu/Debian
brew install tesseract poppler                     # macOS

# 2. Install Ollama (optional, for LLM features)
curl https://ollama.ai/install.sh | sh
ollama pull gemma-3

# 3. Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run the Server

```bash
# Start the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Test it works
curl http://localhost:8080/health
```

### Test the API

```bash
# Parse a document
curl -X POST http://localhost:8080/parse \
  -F "file=@your_document.pdf"

# Expected response:
# {
#   "doctor_name": "Dr. Alice Smith",
#   "patient_name": "John Doe",
#   "dob": "1980-02-14",
#   "confidence": {"doctor": 0.9, "patient": 0.97, "dob": 0.95},
#   "evidence": ["PAGE:1:Patient: John Doe"],
#   "flag_for_review": false
# }
```

## Run with Docker

```bash
# Build and run with docker-compose
docker-compose up -d

# Pull Ollama model
docker-compose exec ollama ollama pull gemma-3

# Test
curl http://localhost:8080/health
```

## Configuration

Create a `.env` file (copy from `.env.example`):

```bash
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=gemma-3
OCR_DPI=300
CONF_THRESHOLD=0.7
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Project Structure

```
medical-parser/
├── app/
│   ├── main.py         # FastAPI endpoints
│   ├── ocr.py          # OCR processing
│   ├── extractor.py    # LLM + regex extraction
│   ├── config.py       # Configuration
│   └── utils.py        # Utilities
├── tests/
│   ├── test_api.py     # API tests
│   ├── test_ocr.py     # OCR tests
│   └── test_extractor.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Features

✅ **OCR Processing** - PDF and image support  
✅ **LLM Extraction** - Local Ollama integration  
✅ **Regex Fallback** - Works without LLM  
✅ **Confidence Scoring** - Auto review flagging  
✅ **Security** - No PHI in logs, local processing  
✅ **Production Ready** - Docker, tests, health checks  

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## Troubleshooting

**Tesseract not found:**
```bash
sudo apt-get install tesseract-ocr
```

**Ollama connection refused:**
```bash
ollama serve
ollama pull gemma-3
```

**Low accuracy:**
- Increase DPI: `export OCR_DPI=600`
- Try different model: `export OLLAMA_MODEL=llama2`

## Security Notes

⚠️ **Important for Production:**

1. **HTTPS**: Deploy behind reverse proxy (nginx, Traefik)
2. **Authentication**: Implement OAuth2 or API keys
3. **Encryption**: Use encrypted volumes for temp files
4. **HIPAA**: Ensure compliance if handling real PHI

This service processes data locally and does not log PHI, but additional security measures are required for production use.

## License

MIT License - See LICENSE file

## Support

For issues and questions, please open a GitHub issue.
