-- Phase 3: resumes tailored to a specific job.

CREATE TABLE tailored_resumes (
    id               TEXT PRIMARY KEY,
    job_id           TEXT REFERENCES jobs(id) ON DELETE SET NULL,
    job_title        TEXT NOT NULL DEFAULT '',
    company          TEXT NOT NULL DEFAULT '',
    data             TEXT NOT NULL,              -- tailored StructuredResume JSON
    changes          TEXT NOT NULL DEFAULT '[]', -- what the tailoring changed
    keywords         TEXT NOT NULL DEFAULT '[]', -- job keywords it emphasised
    guard_notes      TEXT NOT NULL DEFAULT '[]', -- content removed by the rule checks
    fact_check       TEXT,                       -- JSON {status, issues}
    base_hash        TEXT NOT NULL,              -- base resume version it came from
    pdf_path         TEXT,
    pdf_compiled_at  TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE INDEX tailored_by_job ON tailored_resumes (job_id, created_at DESC);
