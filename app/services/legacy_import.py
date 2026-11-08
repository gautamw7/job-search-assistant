"""Import the old JSON stores into SQLite, once, keeping the files as backups.

Runs at startup and lazily before reads, so a legacy file that appears later (an old
backup restored, a script that wrote JSON) is absorbed too. Each file is imported in
one transaction and then renamed to ``<name>.bak-imported-<timestamp>``; nothing is
deleted. Keys are normalized and duplicates merged on the way in.
"""

import json
import threading
import time
from pathlib import Path

from app.core.logging import get_logger
from app.core.settings import DATA_DIR
from app.infra.db import connect
from app.infra.json_store import load_json
from app.infra.linkedin import normalize_url

logger = get_logger(__name__)

_lock = threading.Lock()


def _files() -> dict[str, Path]:
    return {
        "generated_messages": DATA_DIR / "generated_messages.json",
        "enrich_data": DATA_DIR / "enrich_data.json",
        "usage": DATA_DIR / "usage.json",
    }


def _retire(path: Path) -> None:
    path.rename(
        path.with_name(f"{path.name}.bak-imported-{time.strftime('%Y%m%d-%H%M%S')}")
    )


def _import_history(conn, data: dict) -> int:
    from app.services.migrations import _STATUS_RANK

    count = 0
    for raw_url, entry in data.items():
        if not isinstance(entry, dict):
            continue
        url = normalize_url(raw_url)
        extra = {k: v for k, v in entry.items() if k not in ("generations", "tracking")}
        row = conn.execute(
            "SELECT tracking, extra FROM contacts WHERE linkedin_url = ?", (url,)
        ).fetchone()
        tracking = (
            entry.get("tracking") if isinstance(entry.get("tracking"), dict) else None
        )
        if row is None:
            conn.execute(
                "INSERT INTO contacts (linkedin_url, tracking, extra) VALUES (?, ?, ?)",
                (url, json.dumps(tracking) if tracking else None, json.dumps(extra)),
            )
        elif tracking:
            current = json.loads(row["tracking"]) if row["tracking"] else None
            if current is None or _STATUS_RANK.get(
                tracking.get("status"), 0
            ) > _STATUS_RANK.get(current.get("status"), 0):
                conn.execute(
                    "UPDATE contacts SET tracking = ? WHERE linkedin_url = ?",
                    (json.dumps(tracking), url),
                )
        existing = {
            (r["generated_at"], json.loads(r["data"]).get("generated_message"))
            for r in conn.execute(
                "SELECT generated_at, data FROM generations WHERE linkedin_url = ?",
                (url,),
            )
        }
        gens = sorted(
            (g for g in entry.get("generations") or [] if isinstance(g, dict)),
            key=lambda g: str(g.get("generated_at", "")),
        )
        for g in gens:
            key = (g.get("generated_at"), g.get("generated_message"))
            if key in existing:
                continue
            conn.execute(
                "INSERT INTO generations (linkedin_url, generated_at, data) VALUES (?, ?, ?)",
                (url, g.get("generated_at"), json.dumps(g)),
            )
            existing.add(key)
            count += 1
    return count


def _import_profiles(conn, data: dict) -> int:
    count = 0
    for raw_url, entry in data.items():
        if not isinstance(entry, dict):
            continue  # pre-2026 string entries carry no usable structure
        url = normalize_url(raw_url)
        fetched = entry.get("fetched_at")
        row = conn.execute(
            "SELECT fetched_at FROM enriched_profiles WHERE linkedin_url = ?", (url,)
        ).fetchone()
        if row is None or (fetched and (row["fetched_at"] or "") < fetched):
            conn.execute(
                "INSERT OR REPLACE INTO enriched_profiles (linkedin_url, data, fetched_at) VALUES (?, ?, ?)",
                (url, json.dumps(entry), fetched),
            )
            count += 1
    return count


def _import_usage(conn, data: dict) -> int:
    events = data.get("events", []) if isinstance(data, dict) else []
    rows = [
        (e.get("ts", ""), e["kind"], e.get("scope"), json.dumps(e))
        for e in events
        if isinstance(e, dict) and "kind" in e
    ]
    conn.executemany(
        "INSERT INTO usage_events (ts, kind, scope, data) VALUES (?, ?, ?, ?)", rows
    )
    return len(rows)


_IMPORTERS = {
    "generated_messages": _import_history,
    "enrich_data": _import_profiles,
    "usage": _import_usage,
}


def absorb_legacy_json(only: str | None = None) -> dict[str, int]:
    """Import any legacy JSON files present. Cheap no-op when there are none."""
    files = {
        k: p for k, p in _files().items() if (only is None or k == only) and p.exists()
    }
    if not files:
        return {}
    imported: dict[str, int] = {}
    with _lock:
        for name, path in files.items():
            if not path.exists():
                continue  # another thread got here first
            data = load_json(path, default={})
            with connect() as conn:
                imported[name] = _IMPORTERS[name](
                    conn, data if isinstance(data, dict) else {}
                )
            if path.exists():  # a corrupt file was already quarantined by load_json
                _retire(path)
            logger.warning(
                "imported %s records from %s into SQLite", imported[name], path.name
            )
    return imported
