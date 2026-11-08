.PHONY: install test lint format check run tauri-dev tauri-build build-sidecar fetch-tectonic

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
	uv run pyinstaller --clean --noconfirm --distpath binaries --workpath build/pyinstaller job-search-api.spec
	mv binaries/job-search-api binaries/job-search-api-$$(rustc -vV | sed -n 's/^host: //p')
	chmod +x binaries/job-search-api*

# Tectonic compiles tailored resumes to PDF without a TeX Live install. It is
# bundled with the desktop app (externalBin) and kept out of git.
TECTONIC_VERSION ?= 0.17.0
fetch-tectonic:
	@mkdir -p binaries
	@TRIPLE=$$(rustc -vV | sed -n 's/^host: //p'); OUT=binaries/tectonic-$$TRIPLE; \
	if [ -x "$$OUT" ]; then echo "tectonic already present: $$OUT"; exit 0; fi; \
	case "$$TRIPLE" in \
	  *linux*) ASSET_TRIPLE="$$(uname -m)-unknown-linux-musl" ;; \
	  *darwin*) ASSET_TRIPLE="$$TRIPLE" ;; \
	  *) echo "Unsupported platform $$TRIPLE: install Tectonic manually as $$OUT"; exit 1 ;; \
	esac; \
	URL="https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40$(TECTONIC_VERSION)/tectonic-$(TECTONIC_VERSION)-$$ASSET_TRIPLE.tar.gz"; \
	echo "downloading $$URL"; \
	curl -fsSL "$$URL" | tar -xz -C binaries tectonic && mv binaries/tectonic "$$OUT" && chmod +x "$$OUT" && echo "installed $$OUT"

tauri-dev: fetch-tectonic
	npm --prefix frontend run build
	cargo tauri dev

tauri-build: build-sidecar fetch-tectonic
	cargo tauri build

tree:
	tree -d -L 3 --gitignore 2>/dev/null || tree -d -L 3 -I 'node_modules|target|.venv|__pycache__|dist|.git' | head -n 100
