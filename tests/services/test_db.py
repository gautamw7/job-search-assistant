import sqlite3
from pathlib import Path

import pytest

from app.infra import db


def test_migrations_apply_once_and_record_version(tmp_path):
    path = tmp_path / "t.db"
    latest = len(db.available_migrations())
    assert db.migrate(path) == latest
    assert db.migrate(path) == latest  # idempotent, no backup when nothing to do
    assert not list(tmp_path.glob("*.bak-*"))
    with sqlite3.connect(path) as conn:
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert {"base_resume", "search_profile"} <= tables


def test_upgrade_backs_up_and_failed_step_rolls_back(tmp_path, monkeypatch):
    path = tmp_path / "t.db"
    db.migrate(path)
    version = len(db.available_migrations())
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    for v, p in db.available_migrations():
        (migrations / p.name).write_text(p.read_text())
    bad = migrations / f"{version + 1:03d}_broken.sql"
    bad.write_text("CREATE TABLE ok_table (id INTEGER);\nTHIS IS NOT SQL;")
    monkeypatch.setattr(db, "MIGRATIONS_DIR", migrations)

    with pytest.raises(sqlite3.Error):
        db.migrate(path)
    assert len(list(tmp_path.glob("t.db.bak-*"))) == 1  # backed up before trying
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == version
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert "ok_table" not in tables  # the partial step was rolled back


def test_migration_files_must_be_contiguous(tmp_path, monkeypatch):
    (tmp_path / "001_a.sql").write_text("SELECT 1;")
    (tmp_path / "003_c.sql").write_text("SELECT 1;")
    monkeypatch.setattr(db, "MIGRATIONS_DIR", Path(tmp_path))
    with pytest.raises(RuntimeError, match="without gaps"):
        db.available_migrations()
