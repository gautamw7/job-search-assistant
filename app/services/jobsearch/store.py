"""Job persistence: upsert with de-duplication across sources, listing, status."""

import hashlib
import json
import re
from datetime import datetime

from app.infra.db import connect
from app.services.jobsearch.sources.base import JobPosting

STATUSES = ("new", "saved", "applied", "dismissed")
_STOP = {
    "gmbh",
    "inc",
    "ltd",
    "llc",
    "pvt",
    "private",
    "limited",
    "ag",
    "se",
    "co",
    "the",
}


def _norm(text: str) -> str:
    words = re.sub(r"[^a-z0-9]+", " ", (text or "").casefold()).split()
    return " ".join(w for w in words if w not in _STOP)


def dedupe_key(p: JobPosting) -> str:
    city = (p.location or "").split(",")[0]
    title = re.sub(
        r"\(?\b(m|f|w|d|x|all genders)\b(\s*/\s*\b(m|f|w|d|x)\b)*\)?",
        " ",
        p.title,
        flags=re.IGNORECASE,
    )
    return f"{_norm(p.company)}|{_norm(title)}|{_norm(city)}"


def _job_id(key: str) -> str:
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def upsert_postings(postings: list[JobPosting]) -> list[str]:
    """Insert/merge postings; returns ids of jobs touched (excluding dismissed)."""
    now = _now()
    touched: list[str] = []
    with connect() as conn:
        for p in postings:
            key = dedupe_key(p)
            job_id = _job_id(key)
            source = {"source": p.source, "url": p.url, "external_id": p.external_id}
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row is None:
                conn.execute(
                    """INSERT INTO jobs (id, dedupe_key, title, company, location, country,
                       description, description_is_snippet, url, sources, posted_at,
                       salary_min, salary_max, salary_currency, remote, seniority,
                       employment_type, company_size, company_url, applicants,
                       first_seen_at, last_seen_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        job_id,
                        key,
                        p.title,
                        p.company,
                        p.location,
                        p.country,
                        p.description,
                        int(p.description_is_snippet),
                        p.url,
                        json.dumps([source]),
                        p.posted_at,
                        p.salary_min,
                        p.salary_max,
                        p.salary_currency,
                        p.remote,
                        p.seniority,
                        p.employment_type,
                        p.company_size,
                        p.company_url,
                        p.applicants,
                        now,
                        now,
                    ),
                )
                touched.append(job_id)
                continue
            sources = json.loads(row["sources"])
            if not any(s["source"] == p.source and s["url"] == p.url for s in sources):
                sources.append(source)
            # Prefer the fuller description and any extra detail the new source has.
            better_desc = (
                row["description_is_snippet"] and not p.description_is_snippet
            ) or (
                len(p.description) > len(row["description"])
                and p.description_is_snippet == bool(row["description_is_snippet"])
            )
            conn.execute(
                """UPDATE jobs SET sources = ?, last_seen_at = ?,
                   description = CASE WHEN ? THEN ? ELSE description END,
                   description_is_snippet = CASE WHEN ? THEN ? ELSE description_is_snippet END,
                   embedding = CASE WHEN ? THEN NULL ELSE embedding END,
                   company_size = COALESCE(company_size, ?), company_url = COALESCE(company_url, ?),
                   applicants = COALESCE(?, applicants), seniority = COALESCE(seniority, ?),
                   remote = COALESCE(remote, ?), posted_at = COALESCE(posted_at, ?),
                   url = CASE WHEN ? = 'apify' THEN ? ELSE url END
                   WHERE id = ?""",
                (
                    json.dumps(sources),
                    now,
                    better_desc,
                    p.description,
                    better_desc,
                    int(p.description_is_snippet),
                    better_desc,
                    p.company_size,
                    p.company_url,
                    p.applicants,
                    p.seniority,
                    p.remote,
                    p.posted_at,
                    p.source,
                    p.url,
                    job_id,
                ),
            )
            if row["status"] != "dismissed":
                touched.append(job_id)
    return list(dict.fromkeys(touched))


def _row_to_job(row) -> dict:
    job = dict(row)
    job.pop("embedding", None)
    job["sources"] = json.loads(job["sources"] or "[]")
    job["score_breakdown"] = (
        json.loads(job["score_breakdown"]) if job["score_breakdown"] else None
    )
    job["review"] = json.loads(job["review"]) if job["review"] else None
    job["description_is_snippet"] = bool(job["description_is_snippet"])
    return job


def get_jobs(
    ids: list[str] | None = None,
    statuses: tuple[str, ...] = ("new", "saved", "applied"),
) -> list[dict]:
    with connect() as conn:
        if ids is not None:
            if not ids:
                return []
            marks = ",".join("?" * len(ids))
            rows = conn.execute(
                f"SELECT * FROM jobs WHERE id IN ({marks})", ids
            ).fetchall()
        else:
            marks = ",".join("?" * len(statuses))
            rows = conn.execute(
                f"SELECT * FROM jobs WHERE status IN ({marks}) ORDER BY score DESC NULLS LAST, last_seen_at DESC",
                statuses,
            ).fetchall()
    return [_row_to_job(r) for r in rows]


def rows_for_ranking(ids: list[str]) -> list[dict]:
    """Jobs including raw embedding blobs (for scoring)."""
    if not ids:
        return []
    with connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM jobs WHERE id IN ({','.join('?' * len(ids))})", ids
        ).fetchall()
    return [dict(r) for r in rows]


def save_embeddings(pairs: list[tuple[str, bytes]], model: str) -> None:
    with connect() as conn:
        conn.executemany(
            "UPDATE jobs SET embedding = ?, embedding_model = ? WHERE id = ?",
            [(blob, model, job_id) for job_id, blob in pairs],
        )


def save_scores(scores: list[tuple[str, float, dict]]) -> None:
    with connect() as conn:
        conn.executemany(
            "UPDATE jobs SET score = ?, score_breakdown = ? WHERE id = ?",
            [
                (score, json.dumps(breakdown), job_id)
                for job_id, score, breakdown in scores
            ],
        )


def save_review(job_id: str, review: dict, score: float, breakdown: dict) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE jobs SET review = ?, score = ?, score_breakdown = ? WHERE id = ?",
            (json.dumps(review), score, json.dumps(breakdown), job_id),
        )


def save_full_description(job_id: str, text: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE jobs SET description = ?, description_is_snippet = 0, embedding = NULL WHERE id = ?",
            (text, job_id),
        )


def set_status(job_id: str, status: str) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {', '.join(STATUSES)}")
    with connect() as conn:
        cur = conn.execute(
            "UPDATE jobs SET status = ?, status_changed_at = ? WHERE id = ?",
            (status, _now(), job_id),
        )
        if cur.rowcount == 0:
            raise LookupError("Job not found")
    return get_jobs([job_id])[0]
