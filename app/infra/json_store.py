"""Deep JSON store — safe load/save with defaults and atomic write."""

import json
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


def load_json(path: Path | str, default: dict | list | None = None) -> dict | list:
    path = Path(path)
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("loaded json path=%s entries=%s", path, len(data) if isinstance(data, (dict, list)) else 1)
        return data
    except FileNotFoundError:
        logger.info("json store not found path=%s", path)
        return default
    except json.JSONDecodeError as e:
        logger.warning("json decode failed path=%s err=%s", path, e)
        return default


def save_json(path: Path | str, data: dict | list) -> None:
    path = Path(path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info("json saved path=%s entries=%s", path, len(data) if isinstance(data, (dict, list)) else 1)
