"""Central Pydantic schemas for API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

from app.infra.linkedin import is_linkedin_profile_url, normalize_url


class APIKeyRequest(BaseModel):
    api_key: str


class AdzunaKeyRequest(BaseModel):
    app_id: str
    app_key: str


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


class Target(BaseModel):
    linkedin_url: str
    additional_note: str | None = None
    additional_preferences: MessagePreferences | None = None
    # Re-scrape the profile instead of using the cached enrichment.
    refresh_profile: bool = False

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, value: str) -> str:
        if not is_linkedin_profile_url(value):
            raise ValueError("Invalid LinkedIn profile URL")
        return normalize_url(value)


class FactIssue(BaseModel):
    claim: str
    reason: str = ""


class FactCheck(BaseModel):
    status: Literal["pass", "flagged", "skipped", "error"]
    issues: list[FactIssue] = []
    error: str | None = None


class MessageResponse(BaseModel):
    linkedin_url: str
    generated_message: str | None = None
    generated_at: str | None = None
    status: Literal["success", "failed"]
    error: str | None = None
    fact_check: FactCheck | None = None
    shared_background: list[str] = []


COMMUNICATION_SOURCES = ("response", "questions", "default")


class UserCommunication(BaseModel):
    content: str
    style: str
    source: Literal["response", "questions", "default"]
    saved_at: datetime


class JobTargetState(BaseModel):
    linkedin_url: str
    status: Literal[
        "queued", "enriching", "drafting", "checking", "success", "failed", "cancelled"
    ]
    generated_message: str | None = None
    generated_at: str | None = None
    error: str | None = None
    fact_check: FactCheck | None = None
    shared_background: list[str] = []


class UsageTotals(BaseModel):
    brightdata_profiles: int = 0
    gemini_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float | None = None


class JobState(BaseModel):
    job_id: str
    status: Literal["running", "done", "cancelled"]
    targets: list[JobTargetState]
    usage: UsageTotals = UsageTotals()


class TrackingUpdate(BaseModel):
    linkedin_url: str
    status: Literal["drafted", "sent", "replied", "interviewing", "closed"] | None = (
        None
    )
    notes: str | None = None
    followup_sent: bool = False


class BatchEnrichRequest(BaseModel):
    linkedin_urls: list[str]
    refresh: bool = False


class SettingsUpdate(BaseModel):
    pricing: dict[str, float | None] | None = None
    budget: dict[str, float | None] | None = None
    fact_check_enabled: bool | None = None
