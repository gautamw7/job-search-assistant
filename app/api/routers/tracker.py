from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.schemas import TrackingUpdate
from app.core.logging import get_logger
from app.services import tracker

logger = get_logger(__name__)

router = APIRouter(prefix="/tracker", tags=["tracker"])


@router.get("/")
def list_contacts():
    """Every contact with a generated message, its status and follow-up timing."""
    return {
        "contacts": tracker.list_contacts(),
        "statuses": list(tracker.STATUSES),
        "followup_after_days": tracker.FOLLOWUP_AFTER_DAYS,
        "max_followups": tracker.MAX_FOLLOWUPS,
    }


@router.post("/update")
def update_contact(req: TrackingUpdate):
    try:
        return tracker.update_tracking(
            req.linkedin_url,
            status=req.status,
            notes=req.notes,
            followup_sent=req.followup_sent,
        )
    except tracker.ContactNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class BulkUpdate(BaseModel):
    linkedin_urls: list[str]
    status: Literal["drafted", "sent", "replied", "interviewing", "closed"]


@router.post("/bulk")
def bulk_update_contacts(req: BulkUpdate):
    """e.g. mark every drafted message as sent in one action."""
    if not req.linkedin_urls:
        raise HTTPException(status_code=400, detail="No contacts selected.")
    return tracker.bulk_update(req.linkedin_urls, req.status)
