"""SQLite access + schema migrations.

Migrations are plain numbered SQL files in ``app/db/migrations`` (``001_x.sql``,
``002_y.sql``…). The applied version is stored in the database itself
(``PRAGMA user_version``), so there is no extra bookkeeping table. Before
upgrading an existing database we take a consistent copy with SQLite's backup
API, so a bad migration can always be rolled back by restoring that file.

Each call to :func:`connect` opens a fresh connection (cheap for SQLite) in WAL
mode, which allows concurrent readers alongside one writer across threads.
"""

import re
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.core.logging import get_logger
from app.core.settings import DATA_DIR

logger = get_logger(__name__)

DB_FILE = "app.db"
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "db" / "migrations"
_MIGRATION_RE = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")
_migrate_lock = threading.Lock()
_migrated_paths: set[str] = set()


def db_path() -> Path:
    return DATA_DIR / DB_FILE


def _open(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def available_migrations() -> list[tuple[int, Path]]:
    found = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        match = _MIGRATION_RE.match(path.name)
        if not match:
            raise RuntimeError(f"Badly named migration file: {path.name}")
        found.append((int(match.group(1)), path))
    versions = [v for v, _ in found]
    if versions != list(range(1, len(versions) + 1)):
        raise RuntimeError(
            f"Migrations must be numbered 001, 002, … without gaps: {versions}"
        )
    return found


def schema_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _backup(conn: sqlite3.Connection, path: Path, version: int) -> Path:
    target = path.with_name(
        f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}-v{version}"
    )
    with sqlite3.connect(target) as dest:
        conn.backup(dest)
    return target


def migrate(path: Path | None = None) -> int:
    """Apply pending migrations; returns the resulting schema version."""
    path = path or db_path()
    with _migrate_lock:
        conn = _open(path)
        try:
            current = schema_version(conn)
            pending = [(v, p) for v, p in available_migrations() if v > current]
            if not pending:
                return current
            if current > 0:
                backup = _backup(conn, path, current)
                logger.info("database backed up before migration to=%s", backup.name)
            for version, file in pending:
                sql = file.read_text(encoding="utf-8")
                # executescript commits implicitly; wrap so a failure rolls back this step.
                conn.executescript(
                    f"BEGIN;\n{sql}\nPRAGMA user_version = {version};\nCOMMIT;"
                )
                logger.info("applied migration %s", file.name)
            return schema_version(conn)
        except Exception:
            conn.rollback()
            logger.exception("database migration failed at path=%s", path)
            raise
        finally:
            conn.close()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Connection with the schema guaranteed current. Commits on success."""
    path = db_path()
    key = str(path)
    if key not in _migrated_paths:
        migrate(path)
        _migrated_paths.add(key)
    conn = _open(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
