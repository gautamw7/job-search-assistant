import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from job_search_assistant.api.schemas import UserCommunication
from job_search_assistant.services.logger import get_logger
from job_search_assistant.services.paths import PROJECT_ROOT as ROOT_DIR
from job_search_assistant.services.user_communication import (
    get_user_communication_prompt,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/user-communication",
    tags=["user-communication"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
async def get_user_communication():
    """
    Get the currently saved user communication style.

    If no style has been saved, return the default style.
    """
    config = get_user_communication_prompt()

    output_path = config.get(
        "output_path",
        "data/user_communication_style.json",
    )
    if not os.path.isabs(output_path):
        output_path = ROOT_DIR / output_path
    else:
        output_path = Path(output_path)

    try:
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Ensure backwards compatibility with dicts lacking 'style' key
        content = data.get("content", data.get("style", ""))

        # Clean up invalid event serialization if present
        if not content or content == '{"isTrusted":true}':
            logger.warning(
                "user communication invalid content event serialization, returning default"
            )
            default_content = config.get("default", "")
            return UserCommunication(
                content=default_content,
                style=default_content,
                source="default",
                saved_at=datetime.now(),
            )

        source = data.get("source", "response")
        saved_at = data.get("saved_at", datetime.now().isoformat())

        logger.debug("user communication loaded source=%s path=%s", source, output_path)
        return UserCommunication(
            content=content,
            style=content,
            source=source,
            saved_at=saved_at,
        )

    except FileNotFoundError:
        logger.info(
            "user communication file not found, returning default path=%s", output_path
        )
        default_content = config.get("default", "")
        return UserCommunication(
            content=default_content,
            style=default_content,
            source="default",
            saved_at=datetime.now(),
        )
    except Exception as e:
        logger.exception(
            "failed to load user communication path=%s err=%s", output_path, e
        )
        default_content = config.get("default", "")
        return UserCommunication(
            content=default_content,
            style=default_content,
            source="default",
            saved_at=datetime.now(),
        )


@router.get("/prompt")
async def get_prompt():
    """
    Get the configuration needed by the frontend
    to build the user communication flow.
    """
    config = get_user_communication_prompt()
    logger.debug(
        "user communication prompt served questions=%s",
        len(config.get("questions", [])),
    )

    return {
        "prompt": config.get("prompt", ""),
        "default": config.get("default", ""),
        "questions": config.get("questions", []),
    }


@router.post("/update")
async def update_user_communication(request: Request):
    """
    Save the final user communication style.
    Accepts either a plain string or a JSON object with content/source.
    """
    try:
        body = await request.json()
    except Exception:
        body = ""

    if isinstance(body, str):
        content = body.strip()
        source = "response"
    elif isinstance(body, dict):
        content = str(body.get("content", body.get("style", ""))).strip()
        source = body.get("source", "response")
    else:
        content = str(body).strip()
        source = "response"

    if not content:
        logger.warning("update user communication rejected: empty content")
        raise HTTPException(
            status_code=400, detail="Communication style cannot be empty."
        )

    config = get_user_communication_prompt()

    output_path = config.get(
        "output_path",
        "data/user_communication_style.json",
    )
    if not os.path.isabs(output_path):
        output_path = ROOT_DIR / output_path
    else:
        output_path = Path(output_path)

    directory = os.path.dirname(output_path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    saved_at = datetime.now()

    user_communication = {
        "content": content,
        "style": content,
        "source": source,
        "saved_at": saved_at.isoformat(),
    }

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                user_communication,
                f,
                ensure_ascii=False,
                indent=4,
            )

        logger.info(
            "user communication saved source=%s path=%s len=%s",
            source,
            output_path,
            len(content),
        )
        return user_communication

    except OSError as z:
        logger.exception(
            "failed to save user communication path=%s err=%s", output_path, z
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save user communication style: {z!s}",
        )
