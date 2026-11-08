"""Internal: message history + tracker persistence (SQLite).

Tables ``contacts`` and ``generations`` (migration 004). The dict shape returned by
``load_generated_messages`` is the same one the JSON file used, so callers did not
change: ``{url: {"generations": [...], "tracking": {...}, ...legacy extras}}``.
Passing an explicit ``output_path`` still reads/writes that JSON file (scripts,
exports, tests of the legacy format).
"""

import json
import threading
from pathlib import Path

from app.core.settings import GENERATED_MESSAGES as LEGACY_PATH
from app.infra.db import connect
from app.infra.json_store import load_json, save_json
from app.services.legacy_import import absorb_legacy_json

_lock = threading.RLock()


def history_lock(_output_path: Path | str | None = None) -> threading.RLock:
    """Lock to hold around a read-modify-write of history/tracking."""
    return _lock


def _is_legacy(path: Path | str | None) -> bool:
    return path is not None and Path(path) != LEGACY_PATH


def _ensure_contact(conn, url: str) -> None:
    conn.execute("INSERT OR IGNORE INTO contacts (linkedin_url) VALUES (?)", (url,))


def load_generated_messages(output_path: Path | str | None = None) -> dict:
    if _is_legacy(output_path):
        data = load_json(output_path, default={})
        return data if isinstance(data, dict) else {}
    absorb_legacy_json("generated_messages")
    with connect() as conn:
        contacts = conn.execute(
            "SELECT linkedin_url, tracking, extra FROM contacts ORDER BY rowid"
        ).fetchall()
        gens = conn.execute(
            "SELECT linkedin_url, data FROM generations ORDER BY id"
        ).fetchall()
    out: dict[str, dict] = {}
    for c in contacts:
        entry = {**json.loads(c["extra"] or "{}"), "generations": []}
        if c["tracking"]:
            entry["tracking"] = json.loads(c["tracking"])
        out[c["linkedin_url"]] = entry
    for g in gens:
        out.setdefault(g["linkedin_url"], {"generations": []})["generations"].append(
            json.loads(g["data"])
        )
    return out


def save_generated_messages(
    messages: dict, output_path: Path | str | None = None
) -> None:
    """Replace the whole history (kept for compatibility; prefer the targeted helpers)."""
    if _is_legacy(output_path):
        save_json(output_path, messages)
        return
    with _lock, connect() as conn:
        conn.execute("DELETE FROM generations")
        conn.execute("DELETE FROM contacts")
        for url, entry in messages.items():
            if not isinstance(entry, dict):
                continue
            extra = {
                k: v for k, v in entry.items() if k not in ("generations", "tracking")
            }
            tracking = entry.get("tracking")
            conn.execute(
                "INSERT INTO contacts (linkedin_url, tracking, extra) VALUES (?, ?, ?)",
                (url, json.dumps(tracking) if tracking else None, json.dumps(extra)),
            )
            conn.executemany(
                "INSERT INTO generations (linkedin_url, generated_at, data) VALUES (?, ?, ?)",
                [
                    (url, g.get("generated_at"), json.dumps(g))
                    for g in entry.get("generations") or []
                ],
            )


def append_generation(url: str, generation: dict) -> None:
    absorb_legacy_json("generated_messages")
    with _lock, connect() as conn:
        _ensure_contact(conn, url)
        conn.execute(
            "INSERT INTO generations (linkedin_url, generated_at, data) VALUES (?, ?, ?)",
            (url, generation.get("generated_at"), json.dumps(generation)),
        )


def get_entry(url: str) -> dict | None:
    """One contact in the legacy dict shape, or None."""
    absorb_legacy_json("generated_messages")
    with connect() as conn:
        c = conn.execute(
            "SELECT tracking, extra FROM contacts WHERE linkedin_url = ?", (url,)
        ).fetchone()
        if c is None:
            return None
        gens = conn.execute(
            "SELECT data FROM generations WHERE linkedin_url = ? ORDER BY id", (url,)
        ).fetchall()
    entry = {
        **json.loads(c["extra"] or "{}"),
        "generations": [json.loads(g["data"]) for g in gens],
    }
    if c["tracking"]:
        entry["tracking"] = json.loads(c["tracking"])
    return entry


def set_tracking(url: str, tracking: dict) -> None:
    with _lock, connect() as conn:
        cur = conn.execute(
            "UPDATE contacts SET tracking = ? WHERE linkedin_url = ?",
            (json.dumps(tracking), url),
        )
        if cur.rowcount == 0:
            raise LookupError(f"No contact found for {url}")
