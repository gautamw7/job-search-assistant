"""Central path definitions for the project.

Single source for REPO_ROOT / APP_DIR / DATA_DIR - explicit, no parent.parent hacks.
pyproject.toml is at repo root, app/ is at repo root / app.
"""

import os
from pathlib import Path


def find_project_root(
    start: Path | None = None,
    markers: tuple[str, ...] = ("pyproject.toml", ".git"),
) -> Path:
    """Walk up from start to find repo root marker.

    Looks for pyproject.toml or .git in parent directories.
    Falls back to 3-level parent (app/services -> repo root).
    """
    cur = Path(start).resolve() if start else Path(__file__).resolve()
    cur = cur if cur.is_dir() else cur.parent
    for parent in [cur, *cur.parents]:
        for marker in markers:
            if (parent / marker).exists():
                return parent
    return Path(__file__).resolve().parent.parent.parent


# Repo root is where pyproject.toml lives (project root)
PROJECT_ROOT = find_project_root()
# Compat alias - REPO_ROOT == PROJECT_ROOT after migration
REPO_ROOT = PROJECT_ROOT
APP_DIR = PROJECT_ROOT / "app"
DATA_DIR_ENV = "JOB_SEARCH_DATA_DIR"
DATA_DIR = (
    Path(os.environ[DATA_DIR_ENV]).expanduser().resolve()
    if os.environ.get(DATA_DIR_ENV)
    else PROJECT_ROOT / "data"
)
PROMPTS_DIR = PROJECT_ROOT / "prompts"
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"

ENRICH_DATA = DATA_DIR / "enrich_data.json"
SECRETS_FILE = DATA_DIR / "secrets.json"
RESUME_PDF = DATA_DIR / "resume.pdf"
RESUME_MD = DATA_DIR / "resume.md"
GENERATED_MESSAGES = DATA_DIR / "generated_messages.json"
USER_COMM_STYLE = DATA_DIR / "user_communication_style.json"

MODEL_CONFIG = CONFIG_DIR / "model_config.yaml"
LOGGING_CONFIG = CONFIG_DIR / "logging.yaml"
