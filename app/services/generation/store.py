"""Internal: generation history persistence via infra.json_store."""

import threading
from pathlib import Path

from app.core.settings import GENERATED_MESSAGES as OUTPUT_PATH
from app.infra.json_store import load_json, path_lock, save_json


def history_lock(output_path: Path | str = OUTPUT_PATH) -> threading.RLock:
    """Lock to hold around a load -> modify -> save of the history file."""
    return path_lock(output_path)


def load_generated_messages(output_path: Path | str = OUTPUT_PATH) -> dict:
    data = load_json(output_path, default={})
    return data if isinstance(data, dict) else {}


def save_generated_messages(
    messages: dict, output_path: Path | str = OUTPUT_PATH
) -> None:
    save_json(output_path, messages)
