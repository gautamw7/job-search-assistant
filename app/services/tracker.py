"""Outreach tracker: where each contact stands and when to follow up.

Tracking lives next to the generated messages (``generated_messages.json`` →
``entry["tracking"]``) so a contact's messages and status can never drift apart.
"""

from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.services.generation.store import (
    get_entry,
    history_lock,
    load_generated_messages,
    set_tracking,
)

logger = get_logger(__name__)

STATUSES = ("drafted", "sent", "replied", "interviewing", "closed")
FOLLOWUP_AFTER_DAYS = 4
MAX_FOLLOWUPS = 2


class ContactNotFoundError(LookupError):
    pass


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def default_tracking() -> dict:
    return {
        "status": "drafted",
        "notes": "",
        "sent_at": None,
        "last_contact_at": None,
        "replied_at": None,
        "followup_count": 0,
        "updated_at": None,
    }


def get_tracking(entry: dict) -> dict:
    stored = entry.get("tracking") if isinstance(entry, dict) else None
    return {**default_tracking(), **(stored or {})}


def followup_due_at(tracking: dict) -> str | None:
    """When a follow-up becomes due, or None if none is expected."""
    if tracking["status"] != "sent" or tracking["followup_count"] >= MAX_FOLLOWUPS:
        return None
    last = tracking.get("last_contact_at") or tracking.get("sent_at")
    if not last:
        return None
    try:
        due = datetime.fromisoformat(last) + timedelta(days=FOLLOWUP_AFTER_DAYS)
    except ValueError:
        return None
    return due.isoformat(timespec="seconds")


def is_followup_due(tracking: dict) -> bool:
    due = followup_due_at(tracking)
    return bool(due) and datetime.fromisoformat(due) <= datetime.now()


def update_tracking(
    linkedin_url: str,
    *,
    status: str | None = None,
    notes: str | None = None,
    followup_sent: bool = False,
) -> dict:
    if status is not None and status not in STATUSES:
        raise ValueError(f"status must be one of {', '.join(STATUSES)}")
    with history_lock():
        entry = get_entry(linkedin_url)
        if not isinstance(entry, dict):
            raise ContactNotFoundError(f"No contact found for {linkedin_url}")
        tracking = get_tracking(entry)
        now = _now()
        if status is not None and status != tracking["status"]:
            tracking["status"] = status
            if status == "sent" and not tracking["sent_at"]:
                tracking["sent_at"] = now
                tracking["last_contact_at"] = now
            if status == "replied" and not tracking["replied_at"]:
                tracking["replied_at"] = now
        if notes is not None:
            tracking["notes"] = notes.strip()[:2000]
        if followup_sent:
            tracking["followup_count"] += 1
            tracking["last_contact_at"] = now
            if tracking["status"] == "drafted":
                tracking["status"] = "sent"
                tracking["sent_at"] = tracking["sent_at"] or now
        tracking["updated_at"] = now
        set_tracking(linkedin_url, tracking)
    logger.info("tracking updated url=%s status=%s", linkedin_url, tracking["status"])
    return tracking


def _days_since(ts: str | None) -> int | None:
    if not ts:
        return None
    try:
        return (datetime.now() - datetime.fromisoformat(ts)).days
    except ValueError:
        return None


def list_contacts() -> list[dict]:
    contacts = []
    for url, entry in load_generated_messages().items():
        if not isinstance(entry, dict):
            continue
        generations = entry.get("generations") or []
        if not generations:
            continue
        tracking = get_tracking(entry)
        latest = generations[-1]
        initial = [g for g in generations if g.get("kind", "outreach") != "followup"]
        contacts.append(
            {
                "linkedin_url": url,
                **tracking,
                "latest_message": latest.get("generated_message", ""),
                "latest_kind": latest.get("kind", "outreach"),
                "latest_at": latest.get("generated_at"),
                "message_count": len(generations),
                "original_message": (initial[-1] if initial else latest).get(
                    "generated_message", ""
                ),
                "followup_due": is_followup_due(tracking),
                "followup_due_at": followup_due_at(tracking),
                "days_since_contact": _days_since(
                    tracking.get("last_contact_at") or tracking.get("sent_at")
                ),
            }
        )
    return contacts
