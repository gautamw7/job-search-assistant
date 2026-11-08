"""Internal: generate, regenerate and follow-up orchestration."""

import time
from collections.abc import Callable
from datetime import datetime

from app.core.logging import get_logger
from app.core.settings import PROMPTS_DIR
from app.infra.config import load_config
from app.services.background import format_hooks, shared_background
from app.services.enrich import get_enrich_data
from app.services.enrich.store import get_profile
from app.services.factcheck import fact_check
from app.services.generation.llm import (
    generate_with_fallback,
    regenerate_with_fallback,
)
from app.services.generation.store import (
    append_generation,
    get_entry,
)
from app.services.resources import build_resources, format_preferences

logger = get_logger(__name__)

StageCallback = Callable[[str], None]


class HistoryNotFoundError(ValueError):
    """Regeneration requested for a profile that has no generated history."""


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _stage(on_stage: StageCallback | None, stage: str) -> None:
    if on_stage:
        on_stage(stage)


def _fetch_profile(linkedin_url: str, refresh: bool) -> str:
    if refresh:
        return get_enrich_data(linkedin_url, force_refresh=True)
    return get_enrich_data(linkedin_url)


def _append_generation(linkedin_url: str, generation: dict) -> None:
    """A single INSERT, so concurrent workers can never lose each other's writes
    (the slow LLM call happens before this)."""
    append_generation(linkedin_url, generation)


def _history_for(linkedin_url: str) -> list[dict]:
    entry = get_entry(linkedin_url)
    if entry is None:
        raise HistoryNotFoundError(f"No history found for URL: {linkedin_url}")
    generations = entry.get("generations", [])
    if not generations:
        raise HistoryNotFoundError(f"No generations found for URL: {linkedin_url}")
    return generations


def _check(
    message: str, resources: dict, recipient: str, note, hooks, on_stage
) -> dict:
    _stage(on_stage, "checking")
    return fact_check(
        message,
        user_resume=resources["user_resume"],
        recipient=recipient,
        user_note=note,
        hooks=hooks,
    )


def generate_outreach(
    linkedin_url: str,
    user_note: str | None = None,
    user_preferences: dict | None = None,
    refresh_profile: bool = False,
    on_stage: StageCallback | None = None,
) -> dict:
    """Generate, fact-check and save a first message. Returns the full record."""
    resources = build_resources()
    pref = (
        user_preferences
        if user_preferences is not None
        else resources["user_preferences"]
    )
    note = (user_note or "").strip() or resources["user_note"]

    _stage(on_stage, "enriching")
    recipient = _fetch_profile(linkedin_url, refresh_profile)
    hooks = shared_background(resources["user_resume"], get_profile(linkedin_url))

    filled_prompt = resources["template"].format(
        user_resume=resources["user_resume"],
        user_communication_style=resources["user_communication_style"],
        user_preferences=format_preferences(pref),
        recipient_enrich_data=recipient,
        shared_background=format_hooks(hooks),
        user_notes=note,
    )
    logger.info(
        "generating outreach url=%s prompt_len=%s hooks=%s",
        linkedin_url,
        len(filled_prompt),
        len(hooks),
    )

    _stage(on_stage, "drafting")
    message = generate_with_fallback(
        filled_prompt, system_prompt=resources["system_prompt"]
    )
    checked = _check(message, resources, recipient, note, hooks, on_stage)

    record = {
        "kind": "outreach",
        "user_note": note,
        "user_preferences": pref,
        "generated_message": message,
        "generated_at": _now(),
        "shared_background": hooks,
        "fact_check": checked,
    }
    _append_generation(linkedin_url, record)
    return record


def generate_outreach_message(
    linkedin_url: str,
    user_note: str | None = None,
    user_preferences: dict | None = None,
    refresh_profile: bool = False,
    on_stage: StageCallback | None = None,
) -> str:
    """Compatibility wrapper returning only the message text."""
    return generate_outreach(
        linkedin_url,
        user_note=user_note,
        user_preferences=user_preferences,
        refresh_profile=refresh_profile,
        on_stage=on_stage,
    )["generated_message"]


def regenerate_responses(
    linkedin_url: str,
    additional_note: str | None = None,
    additional_preferences: dict | None = None,
    on_stage: StageCallback | None = None,
) -> dict:
    generations = _history_for(linkedin_url)
    last_generation = generations[-1]
    current_preferences = (
        additional_preferences
        if additional_preferences is not None
        else last_generation.get("user_preferences", {})
    )

    # Use the *current* resume/style, not a stale snapshot from the first generation.
    resources = build_resources()
    regeneration_prompt = load_config(PROMPTS_DIR / "regeneration_prompt.yaml")[
        "prompt"
    ]

    _stage(on_stage, "enriching")
    recipient = get_enrich_data(linkedin_url)
    hooks = shared_background(resources["user_resume"], get_profile(linkedin_url))

    filled_prompt = regeneration_prompt.format(
        target_content=recipient,
        user_resume=resources["user_resume"],
        user_communication_style=resources["user_communication_style"],
        shared_background=format_hooks(hooks),
        last_generated_message=last_generation["generated_message"],
        additional_note=additional_note or "",
        preferences=format_preferences(current_preferences),
    )
    logger.info(
        "regenerating message url=%s prompt_len=%s", linkedin_url, len(filled_prompt)
    )

    _stage(on_stage, "drafting")
    message = regenerate_with_fallback(
        filled_prompt, system_prompt=resources["system_prompt"]
    )
    checked = _check(message, resources, recipient, additional_note, hooks, on_stage)
    generated_at = _now()
    _append_generation(
        linkedin_url,
        {
            "kind": last_generation.get("kind", "outreach"),
            "user_note": additional_note,
            "user_preferences": current_preferences,
            "generated_message": message,
            "generated_at": generated_at,
            "shared_background": hooks,
            "fact_check": checked,
        },
    )
    return {
        "linkedin_url": linkedin_url,
        "generated_message": message,
        "generated_at": generated_at,
        "shared_background": hooks,
        "fact_check": checked,
    }


def _days_since(ts: str | None) -> int:
    if not ts:
        return 0
    for parse in (
        datetime.fromisoformat,
        lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S"),  # noqa: DTZ007
    ):
        try:
            return max(0, (datetime.now() - parse(ts)).days)
        except ValueError:
            continue
    return 0


def generate_followup(
    linkedin_url: str,
    additional_note: str | None = None,
    on_stage: StageCallback | None = None,
) -> dict:
    """Draft a follow-up for a contact who has not replied. Saved as kind="followup"."""
    from app.services.tracker import get_tracking

    generations = _history_for(linkedin_url)
    entry = get_entry(linkedin_url) or {}
    tracking = get_tracking(entry)
    originals = [g for g in generations if g.get("kind", "outreach") != "followup"]
    followups = [g for g in generations if g.get("kind") == "followup"]
    original = (originals or generations)[-1]

    resources = build_resources()
    template = load_config(PROMPTS_DIR / "followup_prompt.yaml")["prompt"]

    _stage(on_stage, "enriching")
    recipient = get_enrich_data(linkedin_url)
    hooks = shared_background(resources["user_resume"], get_profile(linkedin_url))

    previous = "\n\n".join(f["generated_message"] for f in followups[-2:]) or "None"
    filled_prompt = template.format(
        target_content=recipient,
        user_resume=resources["user_resume"],
        user_communication_style=resources["user_communication_style"],
        original_message=original["generated_message"],
        days_since=_days_since(
            tracking.get("last_contact_at")
            or tracking.get("sent_at")
            or original.get("generated_at")
        ),
        previous_followups=previous,
        shared_background=format_hooks(hooks),
        additional_note=additional_note or "None",
    )

    _stage(on_stage, "drafting")
    message = generate_with_fallback(
        filled_prompt, system_prompt=resources["system_prompt"], purpose="followup"
    )
    checked = _check(message, resources, recipient, additional_note, hooks, on_stage)
    record = {
        "kind": "followup",
        "user_note": additional_note,
        "user_preferences": original.get("user_preferences", {}),
        "generated_message": message,
        "generated_at": _now(),
        "shared_background": hooks,
        "fact_check": checked,
    }
    _append_generation(linkedin_url, record)
    return {"linkedin_url": linkedin_url, **record}
