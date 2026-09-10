"""Internal: generation history persistence via utils.json_store."""

from pathlib import Path

from app.services.paths import GENERATED_MESSAGES as OUTPUT_PATH
from app.utils.json_store import load_json, save_json


def load_generated_messages(output_path: Path | str = OUTPUT_PATH) -> dict:
    return load_json(output_path, default={})


def save_generated_messages(messages: dict, output_path: Path | str = OUTPUT_PATH) -> None:
    save_json(output_path, messages)
