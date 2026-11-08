"""Run a job search in the background: collect → save → embed → score → detail → review.

Only one search runs at a time. A finished search for the same profile is reused for
24 hours unless the user forces a refresh (sources cost money / rate limits).
"""

import json
import threading
import uuid
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.infra.db import connect
from app.services import usage
from app.services.jobsearch import embeddings, ranking, review, store
from app.services.jobsearch.details import fetch_full_description
from app.services.jobsearch.facts import with_facts
from app.services.jobsearch.preferences import source_notes
from app.services.jobsearch.profile import (
    ADZUNA_COUNTRIES,
    SearchProfile,
    confirmed_profile,
    profile_hash,
)
from app.services.jobsearch.sources import ALL_SOURCES, SearchQuery, SourceError
from app.services.jobsearch.sources.apify import ApifyLinkedInSource
from app.services.structured_resume import confirmed_resume

logger = get_logger(__name__)

CACHE_HOURS = 24
SHORTLIST = 50
REVIEW_TOP = 15
STAGES = (
    "collecting",
    "saving",
    "embedding",
    "scoring",
    "details",
    "reviewing",
    "done",
)
_lock = threading.Lock()
_runs: dict[str, dict] = {}


class SearchNotReady(ValueError):
    """Missing confirmed resume/profile or job sources."""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _persist(run: dict) -> None:
    with connect() as conn:
        conn.execute(
            """INSERT INTO job_searches (id, profile_hash, status, started_at, finished_at, stats, notices, error)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET status = excluded.status, finished_at = excluded.finished_at,
                 stats = excluded.stats, notices = excluded.notices, error = excluded.error""",
            (
                run["search_id"],
                run["profile_hash"],
                run["status"],
                run["started_at"],
                run.get("finished_at"),
                json.dumps(run["stats"]),
                json.dumps(run["notices"]),
                run.get("error"),
            ),
        )


def _update(run: dict, **fields) -> None:
    with _lock:
        run.update(fields)


def get_search(search_id: str) -> dict | None:
    with _lock:
        run = _runs.get(search_id)
        if run:
            return {**run, "usage": usage.scope_totals(search_id)}
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM job_searches WHERE id = ?", (search_id,)
        ).fetchone()
    if not row:
        return None
    return {
        "search_id": row["id"],
        "status": row["status"],
        "stage": "done" if row["status"] == "done" else row["status"],
        "message": "",
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "stats": json.loads(row["stats"]),
        "notices": json.loads(row["notices"]),
        "error": row["error"],
        "profile_hash": row["profile_hash"],
        "usage": usage.scope_totals(search_id),
    }


def latest_search() -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM job_searches ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
    return get_search(row["id"]) if row else None


def available_sources() -> dict[str, bool]:
    return {cls.name: cls().available() for cls in ALL_SOURCES}


def start_search(force: bool = False) -> dict:
    resume = confirmed_resume()
    if resume is None:
        raise SearchNotReady("Confirm your structured resume first (Resume tab).")
    profile = confirmed_profile()
    if profile is None:
        raise SearchNotReady("Confirm your search profile first.")
    if not any(available_sources().values()):
        raise SearchNotReady("Add Adzuna or Apify keys in Settings to search for jobs.")
    phash = profile_hash(profile)

    with _lock:
        running = next((r for r in _runs.values() if r["status"] == "running"), None)
    if running:
        return {"search_id": running["search_id"], "cached": False}

    if not force:
        cutoff = (datetime.now() - timedelta(hours=CACHE_HOURS)).isoformat(
            timespec="seconds"
        )
        with connect() as conn:
            row = conn.execute(
                """SELECT id FROM job_searches WHERE status = 'done' AND profile_hash = ? AND started_at >= ?
                   ORDER BY started_at DESC LIMIT 1""",
                (phash, cutoff),
            ).fetchone()
        if row:
            return {"search_id": row["id"], "cached": True}

    run = {
        "search_id": uuid.uuid4().hex,
        "status": "running",
        "stage": "collecting",
        "message": "Searching job sources…",
        "started_at": _now(),
        "finished_at": None,
        "stats": {},
        "notices": [],
        "error": None,
        "profile_hash": phash,
    }
    with _lock:
        _runs[run["search_id"]] = run
    _persist(run)
    threading.Thread(
        target=_run,
        args=(run, profile, resume.to_text()),
        daemon=True,
        name="job-search",
    ).start()
    return {"search_id": run["search_id"], "cached": False}


SENIOR_TERMS = "senior lead principal staff head director manager architect"


def above_level_terms(profile: SearchProfile) -> str | None:
    """Title words to exclude at the source when the user doesn't want senior roles."""
    if not profile.hide_above_level:
        return None
    if {"mid_senior", "director"} & set(profile.experience_levels):
        return None
    return SENIOR_TERMS


def build_query(profile: SearchProfile) -> SearchQuery:
    search = usage.get_settings()["search"]
    return SearchQuery(
        titles=profile.titles[: int(search["max_titles"])],
        countries=profile.countries,
        max_days_old=int(search["max_days_old"]),
        remote=profile.remote,
        employment_types=list(profile.employment_types),
        experience_levels=list(profile.experience_levels),
        posted_days=profile.posted_within_days,
        salary_min=profile.min_salary.amount if profile.min_salary else None,
        salary_currency=profile.min_salary.currency if profile.min_salary else None,
        exclude_terms=above_level_terms(profile),
    )


def preview(profile: SearchProfile) -> dict:
    """The exact searches a run would make, without calling any source."""
    from app.services.jobsearch.preferences import (
        adzuna_params,
        linkedin_params,
        source_notes,
    )
    from app.services.jobsearch.sources.apify import search_url

    query = build_query(profile)
    searches = []
    for country in query.countries:
        for title in query.titles:
            searches.append(
                {
                    "source": "linkedin",
                    "country": country,
                    "title": title,
                    "url": search_url([title], country, linkedin_params(query)),
                }
            )
            if country in ADZUNA_COUNTRIES:
                searches.append(
                    {
                        "source": "adzuna",
                        "country": country,
                        "title": title,
                        "params": adzuna_params(query, country),
                    }
                )
    return {"searches": searches, "notes": source_notes(query)}


def _collect(run: dict, profile: SearchProfile) -> list:
    search = usage.get_settings()["search"]
    query = build_query(profile)
    run["notices"].extend(n for n in source_notes(query) if n not in run["notices"])
    needs_linkedin = [c for c in query.countries if c not in ADZUNA_COUNTRIES]
    if needs_linkedin and not ApifyLinkedInSource().available():
        names = ", ".join(c.upper() for c in needs_linkedin)
        run["notices"].append(
            f"{names} is searched via LinkedIn (Apify), and no Apify token is set. "
            "Add it in Settings to get those jobs."
        )
    postings = []
    for cls in ALL_SOURCES:
        source = cls()
        if not source.available():
            run["notices"].append(
                f"{source.name.capitalize()} isn't set up, so it was skipped."
            )
            continue
        _update(run, message=f"Searching {source.name.capitalize()}…")
        try:
            if source.name == "apify":
                found = source.search(
                    query, max_results=int(search["apify_results_per_search"])
                )
            else:
                found = source.search(
                    query, results_per_query=int(search["adzuna_results_per_query"])
                )
            run["stats"][f"{source.name}_results"] = len(found)
            postings += found
        except (SourceError, usage.BudgetExceededError) as e:
            run["notices"].append(str(e))
            logger.warning("source %s skipped: %s", source.name, e)
    return postings


def _candidates(touched: list[str], max_days: int) -> list[str]:
    """Jobs to (re)score: this search's results plus recent undismissed ones."""
    cutoff = (datetime.now() - timedelta(days=max_days)).isoformat(timespec="seconds")
    with connect() as conn:
        rows = conn.execute(
            "SELECT id FROM jobs WHERE status != 'dismissed' AND last_seen_at >= ?",
            (cutoff,),
        ).fetchall()
    return list(dict.fromkeys(touched + [r["id"] for r in rows]))


def _similarities(
    run: dict, jobs: list[dict], profile: SearchProfile, resume_text: str
) -> dict[str, float] | None:
    """Embedding similarity per job, or None if AI matching is unavailable.

    A failure here must not fail the whole search: ranking falls back to the
    other factors and the user is told why.
    """
    try:
        model, _dims = embeddings.embedding_config()
        need = [j for j in jobs if not j["embedding"] or j["embedding_model"] != model]
        if need:
            vectors = embeddings.embed_texts(
                [f"{j['title']} at {j['company']}\n{j['description']}" for j in need]
            )
            store.save_embeddings(
                [
                    (j["id"], embeddings.to_blob(v))
                    for j, v in zip(need, vectors, strict=True)
                ],
                model,
            )
            for j, v in zip(need, vectors, strict=True):
                j["embedding"] = embeddings.to_blob(v)
        target = embeddings.embed_texts(
            [profile.as_text() + "\n" + resume_text[:3000]]
        )[0]
        return {
            j["id"]: embeddings.cosine(target, embeddings.from_blob(j["embedding"]))
            for j in jobs
        }
    except Exception as e:
        logger.warning("embedding step failed, ranking without similarity: %s", e)
        run["notices"].append(
            "AI matching was unavailable, so jobs were ranked by title, skills, level and location."
        )
        return None


def _run(run: dict, profile: SearchProfile, resume_text: str) -> None:
    try:
        with usage.usage_scope(run["search_id"]):
            _pipeline(run, profile, resume_text)
        _update(run, status="done", stage="done", message="Done", finished_at=_now())
    except Exception as e:
        logger.exception("job search failed id=%s", run["search_id"])
        _update(
            run, status="failed", error=str(e) or type(e).__name__, finished_at=_now()
        )
    _persist(run)


def _pipeline(run: dict, profile: SearchProfile, resume_text: str) -> None:
    from app.services.structured_resume import confirmed_resume

    profile = with_facts(
        profile, confirmed_resume()
    )  # years from the resume, not guessed
    settings = usage.get_settings()["search"]
    max_days, max_emp = (
        int(settings["max_days_old"]),
        int(settings["startup_max_employees"]),
    )

    postings = _collect(run, profile)
    _update(run, stage="saving", message=f"Saving {len(postings)} listings…")
    touched = store.upsert_postings(postings)
    run["stats"]["unique_new_or_updated"] = len(touched)
    ids = _candidates(touched, max_days)
    if not ids:
        _update(run, message="No jobs found.")
        run["notices"].append(
            "No matching jobs were found. Try broader titles or more countries."
        )
        return

    _update(run, stage="embedding", message="Comparing jobs with your profile…")
    jobs = store.rows_for_ranking(ids)
    sims = _similarities(run, jobs, profile, resume_text)

    _update(run, stage="scoring", message="Scoring matches…")
    scored = ranking.score_jobs(jobs, sims, profile, max_days, max_emp)
    store.save_scores(scored)
    scored.sort(key=lambda s: s[1], reverse=True)
    # Above-level jobs are shown (capped) but never spend a paid AI review.
    shortlist = [s for s in scored[:SHORTLIST] if not s[2].get("above_level")]
    top = shortlist[:REVIEW_TOP]
    run["stats"]["scored"] = len(scored)

    _update(run, stage="details", message="Reading full job descriptions…")
    by_id = {j["id"]: j for j in jobs}
    fetched = 0
    for job_id, _, _ in top:
        job = by_id[job_id]
        if job["description_is_snippet"]:
            full = fetch_full_description(job["url"], job["title"], job["description"])
            if full:
                store.save_full_description(job_id, full)
                job["description"], job["description_is_snippet"] = full, 0
                fetched += 1
    run["stats"]["full_descriptions_fetched"] = fetched

    _update(run, stage="reviewing", message=f"Reviewing the top {len(top)} jobs…")
    try:
        reviews = review.review_jobs(
            [by_id[i] for i, _, _ in top], profile, resume_text
        )
    except Exception as e:  # free-tier limit: keep factor scores, tell the user
        reviews = {}
        run["notices"].append(f"Detailed review skipped: {e}")
    for job_id, base, breakdown in top:
        if job_id in reviews:
            score, merged = ranking.apply_review(
                base, breakdown, reviews[job_id], profile
            )
            store.save_review(job_id, reviews[job_id], score, merged)
    run["stats"]["reviewed"] = len(reviews)
