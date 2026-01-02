.PHONY: help install test run docker-build clean

help:
	@echo "Medical Document Parser - Available Commands"
	@echo "install       - Install dependencies"
	@echo "test          - Run tests"
	@echo "run           - Run development server"
	@echo "docker-build  - Build Docker image"
	@echo "clean         - Remove temporary files"

install:
	pip install -r requirements.txt

test:
	pytest --cov=app --cov-report=html

run:
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

docker-build:
	docker build -t medical-parser:latest .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .pytest_cache/ .coverage
