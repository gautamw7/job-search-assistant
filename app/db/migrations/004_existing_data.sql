-- Phase 4: data that used to live in JSON files.

-- One row per LinkedIn contact (was a key in generated_messages.json).
CREATE TABLE contacts (
    linkedin_url  TEXT PRIMARY KEY,
    tracking      TEXT,                          -- JSON tracker state, NULL = drafted
    extra         TEXT NOT NULL DEFAULT '{}'     -- legacy fields kept verbatim
);

-- Every generated message, in order (was entry["generations"]).
CREATE TABLE generations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    linkedin_url  TEXT NOT NULL REFERENCES contacts (linkedin_url) ON DELETE CASCADE,
    generated_at  TEXT,
    data          TEXT NOT NULL                  -- full generation record as JSON
);
CREATE INDEX generations_by_contact ON generations (linkedin_url, id);

-- Scraped LinkedIn profiles (was enrich_data.json).
CREATE TABLE enriched_profiles (
    linkedin_url  TEXT PRIMARY KEY,
    data          TEXT NOT NULL,
    fetched_at    TEXT
);

-- Usage ledger (was usage.json).
CREATE TABLE usage_events (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts     TEXT NOT NULL,
    kind   TEXT NOT NULL,
    scope  TEXT,
    data   TEXT NOT NULL
);
CREATE INDEX usage_events_ts ON usage_events (ts);
