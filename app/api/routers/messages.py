import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException

from app.api.schemas import JobState, MessageResponse, Target
from app.core.logging import get_logger
from app.infra.linkedin import normalize_url
from app.services import jobs
from app.services.generation import (
    generate_followup,
    generate_outreach_message,
    load_generated_messages,
    regenerate_responses,
)
from app.services.generation.service import HistoryNotFoundError

logger = get_logger(__name__)


router = APIRouter(
    prefix="/messages",
    tags=["messages"],
)


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _prefs(target: Target) -> dict | None:
    return (
        target.additional_preferences.model_dump(exclude_none=True)
        if target.additional_preferences
        else None
    )


def _generate_for_target(target: Target) -> str | None:
    """Process exactly one target by delegating to the generator service."""
    logger.info(
        "generating for target url=%s note=%s prefs=%s refresh=%s",
        target.linkedin_url,
        bool(target.additional_note),
        _prefs(target),
        target.refresh_profile,
    )
    kwargs = {
        "linkedin_url": target.linkedin_url,
        "user_note": target.additional_note,
        "user_preferences": _prefs(target),
    }
    if target.refresh_profile:
        kwargs["refresh_profile"] = True
    with jobs.url_lock(target.linkedin_url):
        result = generate_outreach_message(**kwargs)
    logger.info(
        "generation succeeded url=%s len=%s",
        target.linkedin_url,
        len(result) if result else 0,
    )
    return result


def _latest_extras(url: str, message: str | None) -> dict:
    """Fact-check + hooks saved with the latest generation (if it is this message)."""
    generations = (load_generated_messages().get(url) or {}).get("generations") or []
    latest = generations[-1] if generations else {}
    if not message or latest.get("generated_message") != message:
        return {}
    return {
        "fact_check": latest.get("fact_check"),
        "shared_background": latest.get("shared_background") or [],
    }


def _target_dicts(targets: list[Target]) -> list[dict]:
    return [
        {
            "linkedin_url": t.linkedin_url,
            "additional_note": t.additional_note,
            "additional_preferences": _prefs(t),
            "refresh_profile": t.refresh_profile,
        }
        for t in targets
    ]


@router.post("/batch", response_model=list[MessageResponse])
def create_messages_batch(targets: list[Target]):
    """Generate messages for several profiles (blocking). Results keep input order.

    Prefer ``POST /messages/jobs`` for the UI: it reports real progress and can be
    cancelled. This endpoint remains for simple scripted use.
    """
    seen: set[str] = set()
    unique: list[Target] = []
    for target in targets:
        key = target.linkedin_url.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(target)
    logger.info("batch generation start count=%s unique=%s", len(targets), len(unique))

    def run(target: Target) -> MessageResponse:
        try:
            msg = _generate_for_target(target)
            if not msg:
                raise RuntimeError("Generation returned no content.")
            return MessageResponse(
                linkedin_url=target.linkedin_url,
                generated_message=msg,
                generated_at=_now(),
                status="success",
                error=None,
            )
        except Exception as e:
            logger.exception("batch target failed url=%s", target.linkedin_url)
            return MessageResponse(
                linkedin_url=target.linkedin_url,
                generated_message=None,
                generated_at=None,
                status="failed",
                error=str(e) or type(e).__name__,
            )

    with ThreadPoolExecutor(max_workers=jobs.MAX_WORKERS) as executor:
        results = list(executor.map(run, unique))  # map() preserves input order

    success = sum(1 for r in results if r.status == "success")
    logger.info(
        "batch generation done total=%s success=%s failed=%s",
        len(results),
        success,
        len(results) - success,
    )
    return results


@router.post("/", response_model=MessageResponse)
def create_message(target: Target):
    """Generate an outreach message for a single LinkedIn profile."""
    logger.info("single generation start url=%s", target.linkedin_url)
    try:
        msg = _generate_for_target(target)
        if not msg:
            raise RuntimeError("Generation returned no content.")
        return MessageResponse(
            linkedin_url=target.linkedin_url,
            generated_message=msg,
            generated_at=_now(),
            status="success",
            error=None,
            **_latest_extras(target.linkedin_url, msg),
        )
    except Exception as e:
        logger.exception("single generation failed url=%s", target.linkedin_url)
        raise HTTPException(
            status_code=500, detail=f"Message generation failed: {e!s}"
        ) from e


# ---- background jobs (real progress + cancel) --------------------------------


@router.post("/jobs")
def start_generation_job(targets: list[Target]):
    if not targets:
        raise HTTPException(status_code=400, detail="At least one target is required.")
    return {"job_id": jobs.start_job(_target_dicts(targets))}


@router.get("/jobs/{job_id}", response_model=JobState)
def get_generation_job(job_id: str):
    state = jobs.get_job(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return state


@router.delete("/jobs/{job_id}", response_model=JobState)
def cancel_generation_job(job_id: str):
    state = jobs.cancel_job(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return state


# ---- history -----------------------------------------------------------------


@router.get("/targets", response_model=list[str])
def get_target_keys():
    """All LinkedIn profile URLs that have generated history."""
    return list(load_generated_messages().keys())


@router.get("/")
def get_messages(linkedin_url: str | None = None):
    """Latest message for one profile, or the whole history (without heavy context)."""
    messages = load_generated_messages()

    if linkedin_url is not None:
        key = linkedin_url if linkedin_url in messages else normalize_url(linkedin_url)
        if key not in messages:
            logger.warning("messages not found url=%s", linkedin_url)
            raise HTTPException(
                status_code=404, detail=f"No messages found for {linkedin_url}."
            )
        generations = messages[key].get("generations", [])
        if not generations:
            raise HTTPException(
                status_code=404, detail=f"No generations found for {linkedin_url}."
            )
        latest = generations[-1]
        return MessageResponse(
            linkedin_url=key,
            generated_message=latest["generated_message"],
            generated_at=latest["generated_at"],
            status="success",
            error=None,
        )

    # Older entries stored the full resume/prompt per profile; never ship that.
    return {
        url: {k: v for k, v in entry.items() if k != "context"}
        for url, entry in messages.items()
        if isinstance(entry, dict)
    }


@router.post("/regenerate")
def regenerate_message(request: Target):
    logger.info(
        "regenerate start url=%s note=%s",
        request.linkedin_url,
        bool(request.additional_note),
    )
    try:
        response = regenerate_responses(
            linkedin_url=request.linkedin_url,
            additional_note=request.additional_note,
            additional_preferences=_prefs(request),
        )
    except HistoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("regenerate failed url=%s", request.linkedin_url)
        raise HTTPException(status_code=500, detail=str(e)) from e
    return MessageResponse(
        linkedin_url=request.linkedin_url,
        generated_message=response.get("generated_message"),
        generated_at=response.get("generated_at"),
        status="success",
        error=None,
        fact_check=response.get("fact_check"),
        shared_background=response.get("shared_background") or [],
    )


@router.post("/followup", response_model=MessageResponse)
def followup_message(request: Target):
    """Draft a follow-up for a contact who hasn't replied (saved to history)."""
    try:
        record = generate_followup(request.linkedin_url, request.additional_note)
    except HistoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("followup failed url=%s", request.linkedin_url)
        raise HTTPException(status_code=500, detail=str(e)) from e
    return MessageResponse(
        linkedin_url=request.linkedin_url,
        generated_message=record["generated_message"],
        generated_at=record["generated_at"],
        status="success",
        fact_check=record.get("fact_check"),
        shared_background=record.get("shared_background") or [],
    )
