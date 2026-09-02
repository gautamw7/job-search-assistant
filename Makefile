.PHONY: install test lint format check run tauri-dev tauri-build

install:
	uv sync --project backend

test:
	VIRTUAL_ENV= uv run --project backend pytest -v

test-quiet:
	VIRTUAL_ENV= uv run --project backend pytest -q

test-api:
	VIRTUAL_ENV= uv run --project backend pytest -v backend/tests/api

test-services:
	VIRTUAL_ENV= uv run --project backend pytest -v backend/tests/services

lint:
	uv run --project backend ruff check .

format:
	uv run --project backend ruff format .

check:
	uv run --project backend ruff check .
	uv run --project backend ruff format --check .
	VIRTUAL_ENV= uv run --project backend pytest -v

run:
	uv run --project backend uvicorn job_search_assistant.api.main:app --reload --host 127.0.0.1 --port 8000

tauri-dev:
	npm --prefix frontend run build
	cargo tauri dev

tauri-build:
	cargo tauri build
