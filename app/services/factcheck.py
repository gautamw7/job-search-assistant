"""Second-pass fact check: flag claims in a message that the sources don't support.

The generation prompt already forbids invented facts; this verifies it. A failed
check never blocks a message — it is reported as status "error" so the user still
gets the draft, just without the green tick.
"""

import json
import re

from app.core.logging import get_logger
from app.core.settings import PROMPTS_DIR
from app.infra.config import load_config
from app.services import usage
from app.services.background import format_hooks

logger = get_logger(__name__)


def _parse_issues(text: str) -> list[dict]:
    cleaned = re.sub(
        r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE
    ).strip()
    data = json.loads(cleaned)
    items = data.get("issues", []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("fact check returned an unexpected shape")  # noqa: TRY004
    issues = []
    for item in items:
        if isinstance(item, dict) and str(item.get("claim", "")).strip():
            issues.append(
                {
                    "claim": str(item["claim"]).strip()[:300],
                    "reason": str(item.get("reason", "")).strip()[:300],
                }
            )
    return issues


def fact_check(
    message: str,
    *,
    user_resume: str,
    recipient: str,
    user_note: str | None = None,
    hooks: list[str] | None = None,
) -> dict:
    """Return {"status": "pass"|"flagged"|"skipped"|"error", "issues": [...]}."""
    if not usage.get_settings().get("fact_check_enabled", True):
        return {"status": "skipped", "issues": []}

    # Imported here so tests that patch the LLM module see the patched object.
    from app.services.generation.llm import generate_with_fallback

    try:
        template = load_config(PROMPTS_DIR / "fact_check.yaml")["prompt"]
        prompt = template.format(
            user_resume=user_resume,
            recipient=recipient,
            user_note=user_note or "None",
            shared_background=format_hooks(hooks or []),
            message=message,
        )
        raw = generate_with_fallback(prompt, json_mode=True, purpose="fact_check")
        issues = _parse_issues(raw)
    except Exception as e:
        logger.warning("fact check failed: %s", e)
        return {"status": "error", "issues": [], "error": str(e)[:200]}

    return {"status": "flagged" if issues else "pass", "issues": issues}


def fact_check_resume(tailored_text: str, base_text: str) -> dict:
    """Flag claims in a tailored resume that the base resume doesn't support."""
    if not usage.get_settings().get("fact_check_enabled", True):
        return {"status": "skipped", "issues": []}

    from app.services.generation.llm import generate_with_fallback

    try:
        template = load_config(PROMPTS_DIR / "resume_fact_check.yaml")["prompt"]
        raw = generate_with_fallback(
            template.format(base=base_text, tailored=tailored_text),
            json_mode=True,
            purpose="resume_fact_check",
        )
        issues = _parse_issues(raw)
    except Exception as e:
        logger.warning("resume fact check failed: %s", e)
        return {"status": "error", "issues": [], "error": str(e)[:200]}
    return {"status": "flagged" if issues else "pass", "issues": issues}
