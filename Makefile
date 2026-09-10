.PHONY: install test lint format check run tauri-dev tauri-build

install:
	uv sync

test:
	uv run pytest -v

test-quiet:
	uv run pytest -q

test-api:
	uv run pytest -v tests/api

test-services:
	uv run pytest -v tests/services

lint:
	uv run ruff check .

format:
	uv run ruff format .

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest -v

run:
	uv run uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000

build-sidecar:
	mkdir -p binaries
	uv run pyinstaller --name job-search-api --onefile --clean --noconfirm --distpath binaries --workpath /tmp/pyinstaller_build --specpath /tmp app/__main__.py
	mv binaries/job-search-api binaries/job-search-api-x86_64-unknown-linux-gnu 2>/dev/null || true
	chmod +x binaries/job-search-api* || true

tauri-dev:
	npm --prefix frontend run build
	cargo tauri dev

tauri-build: build-sidecar
	cargo tauri build

tree:
	tree -d -L 3 --gitignore 2>/dev/null || tree -d -L 3 -I 'node_modules|target|.venv|__pycache__|dist|.git' | head -n 100
