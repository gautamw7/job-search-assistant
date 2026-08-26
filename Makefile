.PHONY: install test lint format check run

install:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest

run:
	uv run python -m job_search_assistant
