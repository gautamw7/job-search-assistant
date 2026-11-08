import json

from app.infra import db


def test_migration_005_removes_only_unranked_non_india_adzuna_listings(
    tmp_path, monkeypatch
):
    path = tmp_path / "t.db"
    db.migrate(path)  # up to date
    # Pretend the DB is at 004 and replay 005 on rows that exist before it.
    import sqlite3

    conn = sqlite3.connect(path)
    conn.execute("PRAGMA user_version = 4")
    rows = [
        (
            "1",
            "de-adzuna-new",
            "Data Engineer",
            "de",
            "new",
            json.dumps([{"source": "adzuna"}]),
        ),
        (
            "2",
            "de-adzuna-saved",
            "ML Eng",
            "de",
            "saved",
            json.dumps([{"source": "adzuna"}]),
        ),
        ("3", "de-apify-new", "ML Eng", "de", "new", json.dumps([{"source": "apify"}])),
        (
            "4",
            "in-adzuna-new",
            "AI Eng",
            "in",
            "new",
            json.dumps([{"source": "adzuna"}]),
        ),
        (
            "5",
            "de-both-new",
            "DS",
            "de",
            "new",
            json.dumps([{"source": "adzuna"}, {"source": "apify"}]),
        ),
    ]
    for jid, key, title, country, status, sources in rows:
        conn.execute(
            """INSERT INTO jobs (id, dedupe_key, title, company, location, country, description,
               description_is_snippet, url, sources, status, first_seen_at, last_seen_at)
               VALUES (?, ?, ?, 'Co', '', ?, '', 1, '', ?, ?, '2026-11-01', '2026-11-01')""",
            (jid, key, title, country, sources, status),
        )
    conn.commit()
    conn.close()
    migration = next(p for v, p in db.available_migrations() if v == 5)
    conn = sqlite3.connect(path)
    conn.executescript(migration.read_text())
    kept = {r[0] for r in conn.execute("select id from jobs")}
    assert kept == {
        "2",
        "3",
        "4",
        "5",
    }  # only "1" (German, Adzuna-only, unranked) is removed
    conn.close()
