#!/bin/bash
set -e

echo "=========================================="
echo "Medical Document Parser Setup"
echo "=========================================="
echo ""

# Check Python
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    echo "❌ Python 3.11+ required"
    exit 1
fi
echo "✓ Python found"

# Check Tesseract
if ! command -v tesseract &> /dev/null; then
    echo "❌ Tesseract not found. Install with:"
    echo "  Ubuntu/Debian: sudo apt-get install tesseract-ocr"
    echo "  macOS: brew install tesseract"
    exit 1
fi
echo "✓ Tesseract found"

# Create venv
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate and install
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Create directories
mkdir -p temp tests/fixtures
echo "✓ Directories created"

# Copy env file
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "✓ Created .env file"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. source venv/bin/activate"
echo "  2. python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload"
echo "  3. curl http://localhost:8080/health"
echo ""
