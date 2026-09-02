"""Central persistence for generated_messages history.

Replaces scattered json.load in api/routers/messages.py and services/generator.py.
"""

import json
from pathlib import Path

from job_search_assistant.services.logger import get_logger
from job_search_assistant.services.paths import GENERATED_MESSAGES

logger = get_logger(__name__)


def load_generated_messages(path: Path | str = GENERATED_MESSAGES) -> dict:
    path = Path(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("loaded generated messages path=%s entries=%s", path, len(data))
        return data
    except FileNotFoundError:
        logger.info("generated messages file not found path=%s", path)
        return {}
    except Exception as e:
        logger.exception("failed to load generated messages path=%s err=%s", path, e)
        return {}


def save_generated_messages(
    messages: dict, path: Path | str = GENERATED_MESSAGES
) -> None:
    path = Path(path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)
    logger.info("generated messages saved path=%s entries=%s", path, len(messages))


def get_targets(path: Path | str = GENERATED_MESSAGES) -> list[str]:
    data = load_generated_messages(path)
    return list(data.keys())


def get_messages(
    path: Path | str = GENERATED_MESSAGES, linkedin_url: str | None = None
):
    data = load_generated_messages(path)
    if linkedin_url is not None:
        return data.get(linkedin_url)
    return data
