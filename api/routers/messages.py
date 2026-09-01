from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re
from typing import Literal
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from services.generator import (
    generate_outreach_message,
    regenerate_responses,
)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


router = APIRouter(
    prefix="/messages",
    tags=["messages"],
)


class MessagePreferences(BaseModel):
    length: Literal["short", "medium", "detailed"] | None = None
    tone: Literal[
        "professional",
        "friendly",
        "casual",
        "confident",
        "neutral",
    ] | None = None
    formality: Literal[
        "very_casual",
        "casual",
        "balanced",
        "formal",
    ] | None = None
    directness: Literal[
        "very_direct",
        "direct",
        "balanced",
        "gentle",
    ] | None = None
    style: Literal[
        "concise",
        "conversational",
        "polished",
        "natural",
        "persuasive",
    ] | None = None


LINKEDIN_PATTERN = re.compile(
    r"^https://(www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?$"
)


class Target(BaseModel):
    linkedin_url: str
    additional_note: str | None = None
    additional_preferences: MessagePreferences | None = None

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, value: str) -> str:
        if not LINKEDIN_PATTERN.match(value):
            raise ValueError("Invalid LinkedIn profile URL")
        return value


class MessageResponse(BaseModel):
    linkedin_url: str
    generated_message: str | None = None
    generated_at: str | None = None
    status: Literal["success", "failed"]
    error: str | None = None


def _generate_for_target(target: Target) -> str | None:
    """Helper: processes exactly one target by delegating to generator service."""
    prefs = (
        target.additional_preferences.model_dump(exclude_none=True)
        if target.additional_preferences
        else None
    )
    return generate_outreach_message(
        linkedin_url=target.linkedin_url,
        user_note=target.additional_note,
        user_preferences=prefs,
    )


@router.post("/batch", response_model=list[MessageResponse])
def create_messages_batch(targets: list[Target]):
    """
    Generate outreach messages for multiple LinkedIn profiles using multithreading (max 3 workers).
    """
    results = []
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_target = {
            executor.submit(_generate_for_target, target): target
            for target in targets
        }

        for future in as_completed(future_to_target):
            target = future_to_target[future]
            try:
                msg = future.result()
                if not msg:
                    raise RuntimeError("Generation returned no content.")
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
                results.append(
                    MessageResponse(
                        linkedin_url=target.linkedin_url,
                        generated_message=None,
                        generated_at=None,
                        status="failed",
                        error=f"Gemini error: {str(e)}",
                    )
                )

    # If all targets failed due to model/system errors, bubble up as HTTP 500
    if results and all(r.status == "failed" for r in results):
        first_error = results[0].error or "Batch generation failed for all targets."
        raise HTTPException(
            status_code=500,
            detail=f"All batch generations failed: {first_error}"
        )

    return results


@router.post("/", response_model=MessageResponse)
def create_message(target: Target):
    """
    Generate an outreach message for a single LinkedIn profile.
    """
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    try:
        msg = _generate_for_target(target)
        if not msg:
            raise RuntimeError("Generation returned no content.")
        return MessageResponse(
            linkedin_url=target.linkedin_url,
            generated_message=msg,
            generated_at=current_time,
            status="success",
            error=None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Message generation failed: {str(e)}"
        )


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
    except FileNotFoundError:
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
    except FileNotFoundError:
        messages = {}

    if linkedin_url is not None:
        if linkedin_url not in messages:
            raise HTTPException(
                status_code=404,
                detail=f"No messages found for {linkedin_url}.",
            )

        generations = messages[linkedin_url].get("generations", [])
        if not generations:
            raise HTTPException(
                status_code=404,
                detail=f"No generations found for {linkedin_url}.",
            )

        latest_message = generations[-1]
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
        return MessageResponse(
            linkedin_url=request.linkedin_url,
            generated_message=response.get("generated_message"),
            generated_at=response.get("generated_at"),
            status="success",
            error=None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400 if "No history found" in str(e) or "No generations found" in str(e) else 500,
            detail=str(e)
        )
