SHELL := /bin/bash
.PHONY: help install dev lint format type test test-unit test-integration test-contracts \
        run-api run-worker migrate migration scrape compose-up compose-down docker-build clean

PY := python
UV := uv

help:
	@echo "pos-editais-monitor - dev targets"
	@echo ""
	@echo "  install         create venv and install deps (incl. dev)"
	@echo "  dev             install + pre-commit hooks + playwright browsers"
	@echo "  lint            ruff check"
	@echo "  format          ruff format"
	@echo "  type            mypy"
	@echo "  test            full test suite with coverage"
	@echo "  test-unit       only unit tests"
	@echo "  test-integration  tests marked integration (require services up)"
	@echo "  test-contracts  tests against real upstream (network)"
	@echo "  run-api         start FastAPI app (uvicorn)"
	@echo "  run-worker      start scheduler + pipeline worker"
	@echo "  migrate         apply alembic migrations"
	@echo "  migration m=    create new alembic revision"
	@echo "  scrape source=  run a single spider ad-hoc"
	@echo "  compose-up      docker compose up -d"
	@echo "  compose-down    docker compose down -v"

install:
	$(UV) venv
	$(UV) pip install -e ".[dev]"

dev: install
	$(UV) run pre-commit install
	$(UV) run playwright install chromium

lint:
	$(UV) run ruff check src tests

format:
	$(UV) run ruff format src tests
	$(UV) run ruff check --fix src tests

type:
	$(UV) run mypy src

test:
	$(UV) run pytest

test-unit:
	$(UV) run pytest tests/unit

test-integration:
	$(UV) run pytest -m integration

test-contracts:
	$(UV) run pytest -m contract

run-api:
	$(UV) run uvicorn pos_editais_monitor.api.app:app --reload --host 0.0.0.0 --port 8000

run-worker:
	$(UV) run pem worker

migrate:
	$(UV) run alembic upgrade head

migration:
	$(UV) run alembic revision --autogenerate -m "$(m)"

scrape:
	$(UV) run pem scrape --source $(source)

compose-up:
	docker compose -f docker/docker-compose.yml up -d

compose-down:
	docker compose -f docker/docker-compose.yml down -v

docker-build:
	docker build -f docker/Dockerfile -t pos-editais-monitor:dev .

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
