"""Backward-compat shim — use app.utils.json_store + paths.GENERATED_MESSAGES."""

from app.services.paths import GENERATED_MESSAGES
from app.utils.json_store import load_json, save_json

# Re-export with legacy names so existing imports keep working
load_generated_messages = lambda path=GENERATED_MESSAGES: load_json(path, default={})
save_generated_messages = lambda messages, path=GENERATED_MESSAGES: save_json(path, messages)


def get_targets(path=GENERATED_MESSAGES) -> list[str]:
    data = load_json(path, default={})
    if isinstance(data, dict):
        return list(data.keys())
    return []


def get_messages(path=GENERATED_MESSAGES, linkedin_url: str | None = None):
    data = load_json(path, default={})
    if not isinstance(data, dict):
        return None if linkedin_url is not None else {}
    if linkedin_url is not None:
        return data.get(linkedin_url)
    return data
