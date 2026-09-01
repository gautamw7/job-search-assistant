import json
import os
from datetime import datetime
from typing import Literal
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from services.user_communication import get_user_communication_prompt

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

router = APIRouter(
    prefix="/user-communication",
    tags=["user-communication"],
    responses={404: {"description": "Not found"}},
)


class UserCommunication(BaseModel):
    content: str
    style: str
    source: Literal["response", "questions", "default"]
    saved_at: datetime


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
        source = data.get("source", "response")
        saved_at = data.get("saved_at", datetime.now().isoformat())

        return UserCommunication(
            content=content,
            style=content,
            source=source,
            saved_at=saved_at,
        )

    except FileNotFoundError:
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
        raise HTTPException(status_code=400, detail="Communication style cannot be empty.")

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

        return user_communication

    except OSError as z:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save user communication style: {str(z)}",
        )
