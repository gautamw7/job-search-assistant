"""Central Pydantic schemas for API."""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class APIKeyRequest(BaseModel):
    api_key: str


class MessagePreferences(BaseModel):
    length: Literal["short", "medium", "detailed"] | None = None
    tone: (
        Literal[
            "professional",
            "friendly",
            "casual",
            "confident",
            "neutral",
        ]
        | None
    ) = None
    formality: (
        Literal[
            "very_casual",
            "casual",
            "balanced",
            "formal",
        ]
        | None
    ) = None
    directness: (
        Literal[
            "very_direct",
            "direct",
            "balanced",
            "gentle",
        ]
        | None
    ) = None
    style: (
        Literal[
            "concise",
            "conversational",
            "polished",
            "natural",
            "persuasive",
        ]
        | None
    ) = None


LINKEDIN_PATTERN = re.compile(r"^https://(www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?$")


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


class UserCommunication(BaseModel):
    content: str
    style: str
    source: Literal["response", "questions", "default"]
    saved_at: datetime
