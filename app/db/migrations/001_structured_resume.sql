-- Phase 1: the structured base resume (single row) and the job-search profile.

CREATE TABLE base_resume (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    data          TEXT    NOT NULL,             -- StructuredResume as JSON
    source_hash   TEXT    NOT NULL,             -- sha256 of resume.md it was built from
    confirmed_at  TEXT,                         -- NULL until the user reviews it
    updated_at    TEXT    NOT NULL
);

CREATE TABLE search_profile (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    data          TEXT    NOT NULL,             -- SearchProfile as JSON (phase 2)
    source_hash   TEXT    NOT NULL,             -- base resume version it was derived from
    confirmed_at  TEXT,
    updated_at    TEXT    NOT NULL
);
