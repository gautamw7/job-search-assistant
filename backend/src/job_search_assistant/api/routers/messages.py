import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, HTTPException

from job_search_assistant.api.schemas import MessageResponse, Target
from job_search_assistant.services.generator import (
    generate_outreach_message,
    regenerate_responses,
)
from job_search_assistant.services.logger import get_logger
from job_search_assistant.services.paths import PROJECT_ROOT as ROOT_DIR

logger = get_logger(__name__)


router = APIRouter(
    prefix="/messages",
    tags=["messages"],
)


def _generate_for_target(target: Target) -> str | None:
    """Helper: processes exactly one target by delegating to generator service."""
    prefs = (
        target.additional_preferences.model_dump(exclude_none=True)
        if target.additional_preferences
        else None
    )
    logger.info(
        "generating for target url=%s note=%s prefs=%s",
        target.linkedin_url,
        bool(target.additional_note),
        prefs,
    )
    result = generate_outreach_message(
        linkedin_url=target.linkedin_url,
        user_note=target.additional_note,
        user_preferences=prefs,
    )
    logger.info(
        "generation succeeded url=%s len=%s",
        target.linkedin_url,
        len(result) if result else 0,
    )
    return result


@router.post("/batch", response_model=list[MessageResponse])
def create_messages_batch(targets: list[Target]):
    """
    Generate outreach messages for multiple LinkedIn profiles using multithreading (max 3 workers).
    """
    logger.info("batch generation start count=%s", len(targets))
    results = []
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_target = {
            executor.submit(_generate_for_target, target): target for target in targets
        }

        for future in as_completed(future_to_target):
            target = future_to_target[future]
            try:
                msg = future.result()
                if not msg:
                    raise RuntimeError("Generation returned no content.")
                logger.info("batch target success url=%s", target.linkedin_url)
                results.append(
                    MessageResponse(
                        linkedin_url=target.linkedin_url,
                        generated_message=msg,
                        generated_at=current_time,
                        status="success",
                        error=None,
                    )
                )
            except Exception as e:
                logger.exception(
                    "batch target failed url=%s err=%s", target.linkedin_url, e
                )
                results.append(
                    MessageResponse(
                        linkedin_url=target.linkedin_url,
                        generated_message=None,
                        generated_at=None,
                        status="failed",
                        error=f"Gemini error: {e!s}",
                    )
                )

    # If all targets failed due to model/system errors, bubble up as HTTP 500
    if results and all(r.status == "failed" for r in results):
        first_error = results[0].error or "Batch generation failed for all targets."
        logger.error(
            "batch all failed count=%s first_error=%s", len(results), first_error
        )
        raise HTTPException(
            status_code=500, detail=f"All batch generations failed: {first_error}"
        )

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
    """
    Generate an outreach message for a single LinkedIn profile.
    """
    logger.info("single generation start url=%s", target.linkedin_url)
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    try:
        msg = _generate_for_target(target)
        if not msg:
            raise RuntimeError("Generation returned no content.")
        logger.info("single generation success url=%s", target.linkedin_url)
        return MessageResponse(
            linkedin_url=target.linkedin_url,
            generated_message=msg,
            generated_at=current_time,
            status="success",
            error=None,
        )
    except Exception as e:
        logger.exception(
            "single generation failed url=%s err=%s", target.linkedin_url, e
        )
        raise HTTPException(status_code=500, detail=f"Message generation failed: {e!s}")


@router.get("/targets", response_model=list[str])
def get_target_keys():
    """
    Retrieve all LinkedIn profile URLs/keys stored in history.
    """
    messages_path = ROOT_DIR / "data" / "generated_messages.json"
    try:
        with open(
            messages_path,
            "r",
            encoding="utf-8",
        ) as f:
            messages = json.load(f)
        logger.debug("loaded targets count=%s", len(messages))
    except FileNotFoundError:
        logger.info("targets history not found path=%s", messages_path)
        return []
    except Exception as e:
        logger.exception("failed to load targets path=%s err=%s", messages_path, e)
        return []

    return list(messages.keys())


@router.get("/")
def get_messages(linkedin_url: str | None = None):
    """
    Retrieve the latest generated message for a LinkedIn profile,
    or the entire generation history dictionary if no URL is provided.
    """
    messages_path = ROOT_DIR / "data" / "generated_messages.json"
    try:
        with open(
            messages_path,
            "r",
            encoding="utf-8",
        ) as f:
            messages = json.load(f)
        logger.debug(
            "loaded messages url=%s entries=%s", linkedin_url or "all", len(messages)
        )
    except FileNotFoundError:
        logger.info("messages history not found path=%s", messages_path)
        messages = {}
    except Exception as e:
        logger.exception("failed to load messages path=%s err=%s", messages_path, e)
        messages = {}

    if linkedin_url is not None:
        if linkedin_url not in messages:
            logger.warning("messages not found url=%s", linkedin_url)
            raise HTTPException(
                status_code=404,
                detail=f"No messages found for {linkedin_url}.",
            )

        generations = messages[linkedin_url].get("generations", [])
        if not generations:
            logger.warning("no generations url=%s", linkedin_url)
            raise HTTPException(
                status_code=404,
                detail=f"No generations found for {linkedin_url}.",
            )

        latest_message = generations[-1]
        logger.debug(
            "returning latest message url=%s generations=%s",
            linkedin_url,
            len(generations),
        )
        return MessageResponse(
            linkedin_url=linkedin_url,
            generated_message=latest_message["generated_message"],
            generated_at=latest_message["generated_at"],
            status="success",
            error=None,
        )

    return messages


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
            additional_preferences=(
                request.additional_preferences.model_dump(exclude_none=True)
                if request.additional_preferences
                else None
            ),
        )
        logger.info("regenerate success url=%s", request.linkedin_url)
        return MessageResponse(
            linkedin_url=request.linkedin_url,
            generated_message=response.get("generated_message"),
            generated_at=response.get("generated_at"),
            status="success",
            error=None,
        )
    except Exception as e:
        logger.exception("regenerate failed url=%s err=%s", request.linkedin_url, e)
        raise HTTPException(
            status_code=400
            if "No history found" in str(e) or "No generations found" in str(e)
            else 500,
            detail=str(e),
        )
