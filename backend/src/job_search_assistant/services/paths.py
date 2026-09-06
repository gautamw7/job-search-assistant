"""Central path definitions for the project.

Single source for PROJECT_ROOT, DATA_DIR, PROMPTS_DIR, CONFIG_DIR.
Resolves project root by walking up to find pyproject.toml or .project_root marker,
so all other paths stay relative to the project root and no parent.parent chains
need to be updated when files move.
"""

from pathlib import Path


def find_project_root(
    start: Path | None = None,
    markers: tuple[str, ...] = ("pyproject.toml", ".project_root", ".git"),
) -> Path:
    """Walk up from start (or this file) to find project root marker.

    Looks for pyproject.toml or .project_root or .git in parent directories.
    Falls back to 4-level parent (backend/src/job_search_assistant/services -> backend).
    """
    cur = Path(start).resolve() if start else Path(__file__).resolve()
    # start from file's parent if start is a file
    cur = cur if cur.is_dir() else cur.parent
    for parent in [cur, *cur.parents]:
        for marker in markers:
            if (parent / marker).exists():
                return parent
    # Fallback for editable installs / tests
    return Path(__file__).resolve().parent.parent.parent.parent


PROJECT_ROOT = find_project_root()
DATA_DIR = PROJECT_ROOT / "data"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"

ENRICH_DATA = DATA_DIR / "enrich_data.json"
SECRETS_FILE = DATA_DIR / "secrets.json"
RESUME_PDF = DATA_DIR / "resume.pdf"
RESUME_MD = DATA_DIR / "resume.md"
GENERATED_MESSAGES = DATA_DIR / "generated_messages.json"
ENRICH_DATA = DATA_DIR / "enrich_data.json"
USER_COMM_STYLE = DATA_DIR / "user_communication_style.json"

MODEL_CONFIG = CONFIG_DIR / "model_config.yaml"
LOGGING_CONFIG = CONFIG_DIR / "logging.yaml"
