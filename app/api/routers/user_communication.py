from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import UserCommunication
from app.core.logging import get_logger
from app.services.user_communication import (
    get_user_communication_prompt,
    read_saved_style,
    save_style,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/user-communication",
    tags=["user-communication"],
    responses={404: {"description": "Not found"}},
)


def _default_response(config: dict) -> UserCommunication:
    default_content = config.get("default", "")
    return UserCommunication(
        content=default_content,
        style=default_content,
        source="default",
        saved_at=datetime.now(),
    )


@router.get("/")
def get_user_communication():
    """Return the saved communication style, or the default (source="default")."""
    config = get_user_communication_prompt()
    saved = read_saved_style(config)
    if not saved:
        logger.info("no saved user communication, returning default")
        return _default_response(config)
    return UserCommunication(
        content=saved["content"],
        style=saved["content"],
        source=saved["source"],
        saved_at=saved["saved_at"],
    )


@router.get("/prompt")
def get_prompt():
    """Configuration the frontend needs to build the style questionnaire."""
    config = get_user_communication_prompt()
    return {
        "prompt": config.get("prompt", ""),
        "default": config.get("default", ""),
        "questions": config.get("questions", []),
    }


@router.post("/update")
async def update_user_communication(request: Request):
    """Save the final style. Accepts a plain string or {content, source}."""
    try:
        body = await request.json()
    except Exception:
        body = ""

    if isinstance(body, dict):
        content = str(body.get("content", body.get("style", "")))
        source = body.get("source", "response")
    else:
        content = str(body) if body is not None else ""
        source = "response"

    config = get_user_communication_prompt()
    try:
        record = save_style(config, content, source)
    except ValueError as e:
        logger.warning("update user communication rejected: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except OSError as e:
        logger.exception("failed to save user communication err=%s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to save user communication style: {e!s}"
        ) from e

    logger.info("user communication saved source=%s len=%s", source, len(content))
    return record
