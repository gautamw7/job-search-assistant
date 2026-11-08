# ADR 001: Root Layout - app/ + Flat Frontend

Date: 2026-09-07
Status: Accepted

## Context

Previous layout had `backend/pyproject.toml` not at repo root, `backend/.project_root` empty marker, and `find_project_root()` walk that required `ROOT_DIR.parent` hack in `app/api/main.py:28`. `tree -d` showed 887 dirs due to unignored `target/`, `node_modules/`, `.venv/`. `frontend/src/App.tsx` was 1453 LOC god file.

Any small change required loading 5 unrelated services or the entire frontend state.

## Decision

- **Repo root is uv root**: `pyproject.toml` at repo root, package is `app/` (not `job_search_assistant/` to avoid `job-search-assistant/job_search_assistant/` duplication). `uv sync` and `uv run` from root, no `--project backend`.
- **Package layout**: `app/` at root with `app/core/` (settings, logging), `app/infra/` (json_store, linkedin), `app/enrich/`, `app/generation/`, `app/profile/`, `app/system/` + `app/app.py` factory. The old `app/services/*` and `app/utils/*` compatibility shims have been removed; import from `app.core` / `app.infra` directly. Prompts live in `prompts/` (single source of truth).
- **Data/config**: `data/`, `config/`, `prompts/`, `logs/` at repo root, gitignored. Single `app.core.settings.PROJECT_ROOT` explicit, no walk.
- **Frontend**: `frontend/src/app/App.tsx` shell (<250 LOC) + `frontend/src/features/{generator,history,onboarding,profile,settings}/` each <250 LOC, `frontend/src/lib/api-client.ts` env-aware. Old `frontend/src/App.tsx` is now shim re-exporting `app/App`.
- **Tauri**: `src-tauri/src/main.rs` thin, `src-tauri/src/backend.rs` (spawn), `src-tauri/src/paths.rs` (project_root, data_dir). Debug venv at `/.venv`, legacy `backend/.venv` still checked.
- **Tree hygiene**: `.gitignore` + `.ignore` hide `target/`, `node_modules/`, `.venv/`, `__pycache__/`, `logs/`. `make tree` uses `tree -d -L 3 --gitignore`.

## Consequences

- `uv run pytest -q` runs 58 tests, `npm --prefix frontend run build` passes.
- AI token cost: editing `generator` loads 3 files (GeneratorPage + TargetTable + MessageCards) not 1100 LOC.
- No `find_project_root` walk, no `ROOT_DIR.parent` hack.
- Legacy imports `from app.services.paths import DATA_DIR` still work via shims but new code must use `from app.core.settings import DATA_DIR`.

## Guardrails to prevent regression

- Pre-commit: `check-added-large-files --maxkb=500`, `ruff`, file size check (<250 LOC via `max-lines` in eslint/ruff)
- ADR required for any new top-level folder
- `scripts/scaffold-feature.sh` for new frontend features
- Import boundary: `app/enrich` must not import `app/profile` (enforced via ruff `tidy-imports` future)
