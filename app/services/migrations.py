"""One-time data migrations run at startup. Each is idempotent and backs up first.

normalize_keys: older versions stored profiles under the URL exactly as typed
(trailing slash, http, country subdomain). Lookups now use the canonical form, so
legacy keys must be rewritten or those contacts look like they have no history.
"""

import shutil
import time
from pathlib import Path

from app.core.logging import get_logger
from app.core.settings import ENRICH_DATA, GENERATED_MESSAGES
from app.infra.json_store import load_json, path_lock, save_json
from app.infra.linkedin import normalize_url

logger = get_logger(__name__)

_STATUS_RANK = {"drafted": 0, "sent": 1, "closed": 2, "replied": 3, "interviewing": 4}


def _merge_history(entries: list[dict]) -> dict:
    generations = [g for e in entries for g in (e.get("generations") or [])]
    generations.sort(key=lambda g: str(g.get("generated_at", "")))
    merged = {
        k: v
        for e in entries
        for k, v in e.items()
        if k not in ("generations", "tracking")
    }
    merged["generations"] = generations
    trackings = [e["tracking"] for e in entries if isinstance(e.get("tracking"), dict)]
    if trackings:
        merged["tracking"] = max(
            trackings,
            key=lambda t: (
                _STATUS_RANK.get(t.get("status"), 0),
                str(t.get("updated_at") or ""),
            ),
        )
    return merged


def _merge_profile(entries: list) -> dict:
    dicts = [e for e in entries if isinstance(e, dict)]
    if not dicts:
        return entries[-1]
    return max(
        dicts,
        key=lambda e: (str(e.get("fetched_at") or ""), len(e.get("content") or {})),
    )


def _normalize_file(path: Path, merge) -> int:
    with path_lock(path):
        if not path.exists():
            return 0
        data = load_json(path, default={})
        if not isinstance(data, dict) or all(normalize_url(k) == k for k in data):
            return 0
        groups: dict[str, list] = {}
        for key, value in data.items():
            groups.setdefault(normalize_url(key), []).append(value)
        backup = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(path, backup)
        migrated = {
            key: (values[0] if len(values) == 1 else merge(values))
            for key, values in groups.items()
        }
        save_json(path, migrated)
    changed = sum(1 for k in data if normalize_url(k) != k)
    logger.warning(
        "normalized %s legacy keys in %s (backup: %s)", changed, path.name, backup.name
    )
    return changed


def normalize_keys() -> dict[str, int]:
    return {
        "generated_messages": _normalize_file(GENERATED_MESSAGES, _merge_history),
        "enrich_data": _normalize_file(ENRICH_DATA, _merge_profile),
    }


def run_all() -> None:
    try:
        normalize_keys()
    except Exception:
        logger.exception("startup migration failed; data left unchanged")
