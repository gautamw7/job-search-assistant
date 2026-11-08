"""Safe JSON persistence: atomic writes, per-path locks, corruption quarantine.

Guarantees:
- ``save_json`` writes to a temp file and ``os.replace``s it, so a crash mid-write
  can never leave a truncated file behind.
- ``load_json`` never silently discards a corrupt file: it is moved aside to
  ``<name>.corrupt-<timestamp>`` so a later save cannot overwrite the evidence.
- ``update_json`` performs a locked read-modify-write so concurrent threads do not
  lose each other's updates.
"""

import json
import os
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


def path_lock(path: Path | str) -> threading.RLock:
    """Return the process-wide re-entrant lock for ``path``."""
    key = str(Path(path).resolve())
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = _LOCKS[key] = threading.RLock()
        return lock


def _quarantine(path: Path) -> Path | None:
    target = path.with_name(f"{path.name}.corrupt-{time.strftime('%Y%m%d-%H%M%S')}")
    try:
        os.replace(path, target)
        return target
    except OSError:
        logger.exception("could not quarantine corrupt json path=%s", path)
        return None


def load_json(path: Path | str, default: dict | list | None = None) -> dict | list:
    path = Path(path)
    if default is None:
        default = {}
    with path_lock(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.debug(
                "loaded json path=%s entries=%s",
                path,
                len(data) if isinstance(data, (dict, list)) else 1,
            )
            return data
        except FileNotFoundError:
            logger.info("json store not found path=%s", path)
            return default
        except json.JSONDecodeError as e:
            moved = _quarantine(path)
            logger.error(
                "json decode failed path=%s err=%s quarantined_to=%s", path, e, moved
            )
            return default


def save_json(path: Path | str, data: dict | list) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path_lock(path):
        fd, tmp_name = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
    logger.info(
        "json saved path=%s entries=%s",
        path,
        len(data) if isinstance(data, (dict, list)) else 1,
    )


def update_json(
    path: Path | str,
    mutate: Callable[[dict | list], dict | list | None],
    default: dict | list | None = None,
) -> dict | list:
    """Locked read-modify-write. ``mutate`` may edit in place or return new data."""
    path = Path(path)
    with path_lock(path):
        data = load_json(path, default=default)
        result = mutate(data)
        if result is not None:
            data = result
        save_json(path, data)
        return data
