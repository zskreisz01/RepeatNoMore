.PHONY: help install test lint format clean docker-up docker-down docker-logs index run dev

# Default target
help:
	@echo "RepeatNoMore - Available commands:"
	@echo ""
	@echo "  make install      - Install Python dependencies"
	@echo "  make test         - Run all tests"
	@echo "  make test-unit    - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make coverage     - Run tests with coverage report"
	@echo "  make lint         - Run linting checks"
	@echo "  make format       - Format code with ruff"
	@echo "  make typecheck    - Run type checking with mypy"
	@echo "  make clean        - Clean temporary files"
	@echo ""
	@echo "  make docker-up    - Start Docker services"
	@echo "  make docker-down  - Stop Docker services"
	@echo "  make docker-logs  - View Docker logs"
	@echo "  make docker-restart - Restart Docker services"
	@echo ""
	@echo "  make index        - Index knowledge base documents"
	@echo "  make run          - Run the application locally"
	@echo "  make dev          - Run in development mode with reload"
	@echo ""
	@echo "  make examples     - Run example scripts"
	@echo "  make api-demo     - Run API client demo"
	@echo ""

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-asyncio ruff mypy

# Testing
test:
	pytest -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v -m integration

coverage:
	pytest --cov=app --cov-report=html --cov-report=term

test-watch:
	pytest-watch

# Code quality
lint:
	ruff check app/ tests/

format:
	ruff format app/ tests/ examples/

typecheck:
	mypy app/

quality: lint typecheck
	@echo "All quality checks passed!"

# Cleaning
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage build/ dist/

# Docker operations
docker-up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "Services started! Check status with 'make docker-logs'"

docker-down:
	docker-compose down

docker-restart:
	docker-compose restart

docker-logs:
	docker-compose logs -f

docker-logs-app:
	docker-compose logs -f app

docker-logs-chroma:
	docker-compose logs -f chroma

docker-logs-ollama:
	docker-compose logs -f ollama

docker-clean:
	docker-compose down -v
	docker system prune -f

docker-rebuild:
	docker-compose up -d --build app

# Application operations
index:
	curl -X POST http://localhost:8080/api/index \
		-H "Content-Type: application/json" \
		-d '{"directory_path": "./knowledge_base/docs"}'

health:
	curl http://localhost:8080/api/health | json_pp

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8080

dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Examples
examples:
	python examples/basic_usage.py

agent-examples:
	python examples/agent_examples.py

api-demo:
	python examples/api_client.py

# Development helpers
shell:
	docker exec -it repeatnomore_app bash

shell-chroma:
	docker exec -it repeatnomore_chroma sh

shell-ollama:
	docker exec -it repeatnomore_ollama bash

# Database operations
db-reset:
	@echo "Resetting vector database..."
	curl -X POST http://localhost:8080/api/index -H "Content-Type: application/json" -d '{"reset": true}'

db-status:
	@echo "Checking database status..."
	curl http://localhost:8080/api/health | grep -o '"vector_store":"[^"]*"'

# Quick start
quickstart: docker-up
	@echo "Waiting for services to initialize..."
	@sleep 10
	@echo "Indexing knowledge base..."
	@make index
	@echo ""
	@echo "RepeatNoMore is ready!"
	@echo "API docs: http://localhost:8080/docs"
	@echo "Health: http://localhost:8080/api/health"
	@echo ""
	@echo "Try asking a question:"
	@echo "  curl -X POST http://localhost:8080/api/ask \\"
	@echo "    -H 'Content-Type: application/json' \\"
	@echo "    -d '{\"question\": \"How do I get started?\"}'"

# CI/CD
ci-test: install
	pytest --cov=app --cov-report=xml --cov-report=term

ci-lint: install-dev
	ruff check app/ tests/
	mypy app/

ci: ci-lint ci-test
	@echo "CI checks passed!"
