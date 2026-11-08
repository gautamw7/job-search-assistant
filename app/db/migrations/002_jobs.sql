-- Phase 2: job listings, searches and cached embeddings.

CREATE TABLE jobs (
    id                      TEXT PRIMARY KEY,           -- hash of dedupe_key
    dedupe_key              TEXT NOT NULL UNIQUE,       -- company|title|city, normalized
    title                   TEXT NOT NULL,
    company                 TEXT NOT NULL DEFAULT '',
    location                TEXT NOT NULL DEFAULT '',
    country                 TEXT NOT NULL DEFAULT '',   -- ISO-2, lower case
    description             TEXT NOT NULL DEFAULT '',
    description_is_snippet  INTEGER NOT NULL DEFAULT 1,
    url                     TEXT NOT NULL DEFAULT '',   -- best link to show
    sources                 TEXT NOT NULL DEFAULT '[]', -- JSON [{source, url, external_id}]
    posted_at               TEXT,
    salary_min              REAL,
    salary_max              REAL,
    salary_currency         TEXT,
    remote                  TEXT,                       -- remote | hybrid | onsite | NULL
    seniority               TEXT,
    employment_type         TEXT,
    company_size            INTEGER,                    -- employee count when known
    company_url             TEXT,
    applicants              INTEGER,
    embedding               BLOB,                       -- float32 vector
    embedding_model         TEXT,
    status                  TEXT NOT NULL DEFAULT 'new'
                            CHECK (status IN ('new', 'saved', 'applied', 'dismissed')),
    score                   REAL,                       -- final 0-100
    score_breakdown         TEXT,                       -- JSON {factor: 0..1}
    review                  TEXT,                       -- JSON from the LLM re-rank
    first_seen_at           TEXT NOT NULL,
    last_seen_at            TEXT NOT NULL,
    status_changed_at       TEXT
);

CREATE INDEX jobs_status_score ON jobs (status, score DESC);
CREATE INDEX jobs_last_seen ON jobs (last_seen_at);

CREATE TABLE job_searches (
    id            TEXT PRIMARY KEY,
    profile_hash  TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('running', 'done', 'failed')),
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    stats         TEXT NOT NULL DEFAULT '{}',          -- JSON counts per stage/source
    notices       TEXT NOT NULL DEFAULT '[]',          -- JSON list of user-facing notes
    error         TEXT
);

CREATE TABLE embedding_cache (
    key     TEXT PRIMARY KEY,                           -- sha256 of model + text
    model   TEXT NOT NULL,
    vector  BLOB NOT NULL
);
