"""Job search API: profile, searches, listings and statuses."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.logging import get_logger
from app.services import usage
from app.services.enrich.store import get_profile as get_enriched
from app.services.jobsearch import pipeline, store
from app.services.jobsearch import profile as profile_svc
from app.services.jobsearch.ranking import company_kind, language_gap
from app.services.structured_resume import confirmed_resume
from app.services.tracker import list_contacts

logger = get_logger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


class SuggestRequest(BaseModel):
    ambitions: str = ""


class SearchRequest(BaseModel):
    force: bool = False


class StatusRequest(BaseModel):
    status: str


def _resume_or_400():
    resume = confirmed_resume()
    if resume is None:
        raise HTTPException(
            status_code=400, detail="Confirm your structured resume first (Resume tab)."
        )
    return resume


@router.get("/meta")
def meta():
    return {
        "countries": [
            {"code": c, "name": n, "adzuna": c in profile_svc.ADZUNA_COUNTRIES}
            for c, n in sorted(profile_svc.COUNTRY_NAMES.items(), key=lambda kv: kv[1])
        ],
        "language_levels": profile_svc.LANGUAGE_LEVELS,
        "sources": pipeline.available_sources(),
        "resume_confirmed": confirmed_resume() is not None,
    }


@router.get("/profile")
def get_search_profile():
    state = profile_svc.load()
    if not state:
        raise HTTPException(status_code=404, detail="No search profile yet.")
    resume = confirmed_resume()
    stale = (
        resume is not None and profile_svc.resume_hash(resume) != state["source_hash"]
    )
    return {
        "profile": state["profile"].model_dump(),
        "confirmed": state["confirmed"],
        "stale": stale,
    }


@router.post("/profile/suggest")
def suggest_profile(req: SuggestRequest):
    resume = _resume_or_400()
    try:
        suggested, questions = profile_svc.suggest(resume, req.ambitions)
    except Exception as e:
        logger.exception("profile suggestion failed")
        raise HTTPException(
            status_code=502, detail=f"Could not suggest a profile: {e}"
        ) from e
    profile_svc.save(suggested, profile_svc.resume_hash(resume), confirmed=False)
    return {
        "profile": suggested.model_dump(),
        "questions": [q.model_dump() for q in questions],
    }


@router.put("/profile")
def save_search_profile(profile: profile_svc.SearchProfile):
    resume = _resume_or_400()
    if not profile.titles:
        raise HTTPException(status_code=400, detail="Add at least one job title.")
    if not profile.countries:
        raise HTTPException(status_code=400, detail="Add at least one country.")
    state = profile_svc.save(profile, profile_svc.resume_hash(resume), confirmed=True)
    return {"profile": state["profile"].model_dump(), "confirmed": True, "stale": False}


@router.post("/search")
def start_search(req: SearchRequest):
    try:
        return pipeline.start_search(force=req.force)
    except pipeline.SearchNotReady as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/search/latest")
def latest_search():
    run = pipeline.latest_search()
    if not run:
        raise HTTPException(status_code=404, detail="No searches yet.")
    return run


@router.get("/search/{search_id}")
def get_search(search_id: str):
    run = pipeline.get_search(search_id)
    if not run:
        raise HTTPException(status_code=404, detail="Search not found.")
    return run


def _decorate(
    job: dict, profile: profile_svc.SearchProfile | None, max_emp: int
) -> dict:
    """Badges the UI needs, computed in one place."""
    review = job.get("review") or {}
    kind = company_kind(job, max_emp)
    job["company_kind"] = kind or review.get("company_kind") or "unknown"
    job["company_kind_verified"] = kind is not None
    german_level = profile.german_level() if profile else None
    job["german_required"] = review.get("german_required", "unclear")
    job["german_gap"] = job["german_required"] == "yes" and language_gap(
        review.get("german_level"), german_level
    )
    job["sponsorship"] = review.get("sponsorship", "unclear")
    job["via_adzuna"] = any(s["source"] == "adzuna" for s in job["sources"])
    job.pop("dedupe_key", None)
    return job


@router.get("")
def list_jobs(
    status: str = "new,saved,applied",
    country: str | None = None,
    startup_only: bool = False,
    hide_german_required: bool | None = None,
    limit: int = 100,
):
    statuses = tuple(s for s in status.split(",") if s in store.STATUSES) or ("new",)
    profile = profile_svc.confirmed_profile()
    hide_german = (
        profile.hide_german_required
        if (hide_german_required is None and profile)
        else bool(hide_german_required)
    )
    max_emp = int(usage.get_settings()["search"]["startup_max_employees"])
    jobs = []
    for job in store.get_jobs(statuses=statuses):
        job = _decorate(job, profile, max_emp)
        if country and job["country"] != country:
            continue
        if startup_only and job["company_kind"] != "startup":
            continue
        if hide_german and job["german_required"] == "yes":
            continue
        jobs.append(job)
    return {"jobs": jobs[: max(1, min(limit, 500))], "total": len(jobs)}


@router.post("/{job_id}/status")
def set_job_status(job_id: str, req: StatusRequest):
    try:
        job = store.set_status(job_id, req.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    max_emp = int(usage.get_settings()["search"]["startup_max_employees"])
    return _decorate(job, profile_svc.confirmed_profile(), max_emp)


@router.get("/{job_id}/people")
def people_at_company(job_id: str):
    """Tracker contacts whose current company matches this job's company."""
    jobs = store.get_jobs([job_id])
    if not jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    company = store._norm(jobs[0]["company"])
    if not company:
        return []
    people = []
    for contact in list_contacts():
        card = get_enriched(contact["linkedin_url"]).get("card_info") or {}
        theirs = store._norm(card.get("current_company_name") or "")
        if theirs and (theirs == company or theirs in company or company in theirs):
            people.append(
                {
                    "linkedin_url": contact["linkedin_url"],
                    "name": card.get("name") or "",
                    "position": card.get("position") or "",
                    "status": contact["status"],
                }
            )
    return people
