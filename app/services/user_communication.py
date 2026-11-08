"""User communication style: prompt config + the single read/save implementation.

Both the API router and message generation go through these helpers so they can
never disagree about where the style lives or what counts as a valid one.
"""

import os
from datetime import datetime
from pathlib import Path

from app.core.logging import get_logger
from app.core.settings import PROMPTS_DIR, USER_COMM_STYLE
from app.infra.config import load_config
from app.infra.json_store import load_json, save_json

logger = get_logger(__name__)

VALID_SOURCES = ("response", "questions", "default")
MAX_STYLE_CHARS = 8000


def get_user_communication_prompt():
    """Get the user communication prompt and configuration."""
    path = PROMPTS_DIR / "user_communication.yaml"
    if not os.path.exists(path):
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return load_config(str(path))


def style_path(config: dict | None = None) -> Path:
    """Where the saved style lives.

    An absolute ``output_path`` in the prompt config is honoured; the default
    relative ``data/...`` value always maps to the app data dir (never the bundle).
    """
    output_path = (config or {}).get("output_path")
    if output_path and os.path.isabs(output_path):
        return Path(output_path)
    return USER_COMM_STYLE


def validate_style_content(content: str) -> str:
    """Return cleaned content or raise ValueError."""
    content = (content or "").strip()
    if not content:
        raise ValueError("Communication style cannot be empty.")
    if content.startswith('{"isTrusted"'):
        # A DOM event was serialised by mistake instead of the text field value.
        raise ValueError("Invalid communication style content.")
    if len(content) > MAX_STYLE_CHARS:
        raise ValueError(
            f"Communication style is too long (max {MAX_STYLE_CHARS} characters)."
        )
    return content


def read_saved_style(config: dict | None = None) -> dict | None:
    """Return the saved style record, or None if absent/unusable."""
    data = load_json(style_path(config), default={})
    if not isinstance(data, dict):
        return None
    content = data.get("content", data.get("style", ""))
    if not isinstance(content, str) or not content.strip():
        return None
    try:
        validate_style_content(content)
    except ValueError:
        return None
    source = data.get("source")
    return {
        "content": content,
        "source": source if source in VALID_SOURCES else "response",
        "saved_at": data.get("saved_at") or datetime.now().isoformat(),
    }


def save_style(config: dict | None, content: str, source: str = "response") -> dict:
    content = validate_style_content(content)
    if source not in VALID_SOURCES:
        raise ValueError(f"source must be one of {', '.join(VALID_SOURCES)}.")
    record = {
        "content": content,
        "style": content,
        "source": source,
        "saved_at": datetime.now().isoformat(),
    }
    save_json(style_path(config), record)
    return record


def get_user_communication(config: dict) -> str:
    """Return the saved style text, or the configured default."""
    saved = read_saved_style(config)
    if saved:
        logger.info("loaded user communication style len=%s", len(saved["content"]))
        return saved["content"]
    logger.info("no user communication style saved, using default")
    return config["default"]
