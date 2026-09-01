.PHONY: install test lint format check run tauri-dev tauri-build

install:
	uv sync

test:
	PYTHONPATH=. uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest

run:
	uv run uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

tauri-dev:
	cargo tauri dev

tauri-build:
	cargo tauri build
