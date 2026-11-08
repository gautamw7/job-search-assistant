"""Internal: enrich processing — extract, classify, markdown."""

import re

from app.core.logging import get_logger

logger = get_logger(__name__)

CARD_FIELDS = {
    "id",
    "name",
    "url",
    "position",
    "current_company_name",
    "location",
    "followers",
    "connections",
}

CONTENT_FIELDS = {
    "about",
    "country_code",
    "educations_details",
    "education",
    "languages",
    "bio_links",
    "experience",
    "certifications",
}

HIRING_PATTERNS = [
    r"\bhiring\b",
    r"#hiring\b",
    r"\bwe(?:'re| are) hiring\b",
    r"\bjob opening\b",
    r"\bjob openings\b",
    r"\bjob opportunity\b",
    r"\bjob opportunities\b",
    r"\bcareer opportunity\b",
    r"\bcareer opportunities\b",
    r"\bopen position\b",
    r"\bopen positions\b",
    r"\bjob alert\b",
    r"\bwe(?:'re| are) looking for\b",
    r"\bis looking for\b",
    r"\bjoin our team\b",
    r"\bjoin the team\b",
    r"\bapply now\b",
    r"\bapplications? (?:are|is) (?:open|invited)\b",
    r"\b(?:send|share) (?:your|updated) (?:cv|resume)\b",
    r"\brecruit(?:ing|ment)\b",
    r"\bvacanc(?:y|ies)\b",
    r"\bWir suchen\b",
]

HIRING_REGEX = re.compile("|".join(HIRING_PATTERNS), flags=re.IGNORECASE)

# Signals in a person's short headline/bio ("People also viewed" entries) that
# they hire or recruit. A free hint only; scraping their posts is the real check.
CONTACT_SIGNAL_PATTERNS = [
    r"\bwe(?:'re| are) hiring\b",
    r"#hiring\b",
    r"\bhiring\b",
    r"\brecruit(?:er|ers|ing|ment)\b",
    r"\btalent (?:acquisition|partner|scout|lead|manager)\b",
    r"\bhead of (?:talent|people|recruiting)\b",
    r"\bhr (?:manager|business partner|lead)\b",
    r"\bhiring manager\b",
    r"\bstaffing\b",
    r"\bopen roles?\b",
    r"\bjoin (?:my|our) team\b",
]
CONTACT_SIGNAL_REGEX = re.compile(
    "|".join(CONTACT_SIGNAL_PATTERNS), flags=re.IGNORECASE
)


def contact_hiring_signals(text: str | None) -> list[str]:
    """Distinct hiring-related phrases found in a short bio/headline."""
    if not text:
        return []
    seen: list[str] = []
    for match in CONTACT_SIGNAL_REGEX.finditer(text):
        phrase = match.group(0).strip()
        if phrase.lower() not in (s.lower() for s in seen):
            seen.append(phrase)
    return seen


def _extract_card_info(user_data: dict) -> dict:
    return {k: user_data[k] for k in CARD_FIELDS if k in user_data}


def _extract_content(user_data: dict) -> dict:
    return {k: user_data[k] for k in CONTENT_FIELDS if k in user_data}


def _classify_activity(activity: list | None) -> dict:
    hiring: list[dict] = []
    dropped: list[dict] = []
    if not isinstance(activity, list):
        return {"hiring": hiring, "dropped": dropped}
    for post in activity:
        if not isinstance(post, dict):
            dropped.append(post)
            continue
        title = post.get("title")
        if title and HIRING_REGEX.search(title):
            hiring.append(post)
        else:
            dropped.append(post)
    return {"hiring": hiring, "dropped": dropped}


def _extract_discovery(user_data: dict) -> dict:
    people = user_data.get("people_also_viewed")
    if isinstance(people, list):
        return {"people_also_viewed": people}
    return {"people_also_viewed": []}


def _extract_dropped_fields(user_data: dict) -> dict:
    return {
        k: v
        for k, v in user_data.items()
        if k not in CARD_FIELDS
        and k not in CONTENT_FIELDS
        and k not in {"activity", "people_also_viewed"}
    }


def process_enrich_data(user_data: dict) -> dict:
    card_info = _extract_card_info(user_data)
    content = _extract_content(user_data)
    activity = _classify_activity(user_data.get("activity"))
    discovery = _extract_discovery(user_data)
    dropped_fields = _extract_dropped_fields(user_data)
    return {
        "card_info": card_info,
        "content": content,
        "activity": activity,
        "discovery": discovery,
        "dropped_fields": dropped_fields,
    }


MAX_FIELD_CHARS = 1500
MAX_LIST_ITEMS = 12
MAX_HIRING_POSTS = 5


def _clip(text: str, limit: int = MAX_FIELD_CHARS) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _is_empty(value) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _inline(value) -> str:
    """Compact single-line rendering of any JSON value (no Python reprs)."""
    if isinstance(value, dict):
        parts = [f"{k}: {_inline(v)}" for k, v in value.items() if not _is_empty(v)]
        return "; ".join(parts)
    if isinstance(value, list):
        return ", ".join(_inline(v) for v in value if not _is_empty(v))
    return _clip(str(value), 600)


def content_to_markdown(content: dict) -> str:
    md_parts: list[str] = []
    for key, value in content.items():
        md_parts.append(f"## {key}")
        if _is_empty(value):
            md_parts.append("None")
        elif isinstance(value, list):
            for item in value[:MAX_LIST_ITEMS]:
                if isinstance(item, dict):
                    lines = [
                        f"{k}: {_inline(v)}"
                        for k, v in item.items()
                        if not _is_empty(v)
                    ]
                    if lines:
                        md_parts.append(f"- {lines[0]}")
                        md_parts.extend(f"  {line}" for line in lines[1:])
                elif not _is_empty(item):
                    md_parts.append(f"- {_inline(item)}")
            if len(value) > MAX_LIST_ITEMS:
                md_parts.append(f"- (+{len(value) - MAX_LIST_ITEMS} more omitted)")
        elif isinstance(value, dict):
            md_parts.extend(
                f"- {k}: {_inline(v)}" for k, v in value.items() if not _is_empty(v)
            )
        else:
            md_parts.append(_clip(str(value)))
        md_parts.append("")
    return "\n".join(md_parts).strip()


def activity_to_markdown(activity: dict | None) -> str:
    """Recent hiring-related posts — the strongest outreach hook we have."""
    if not isinstance(activity, dict):
        return ""
    posts = [p for p in activity.get("hiring", []) if isinstance(p, dict)]
    lines = []
    for post in posts[:MAX_HIRING_POSTS]:
        title = _clip(str(post.get("title", "")), 300)
        if not title:
            continue
        link = post.get("link") or post.get("url")
        lines.append(f"- {title}" + (f" ({link})" if link else ""))
    return "\n".join(lines)


def is_error_record(profile: dict) -> bool:
    """BrightData can return per-URL error rows instead of a profile."""
    return bool(
        isinstance(profile, dict)
        and (profile.get("error") or profile.get("error_code"))
        and not profile.get("name")
    )


def map_enrich_data_by_url(results: list) -> dict:
    return {
        profile["input_url"]: process_enrich_data(profile)
        for profile in results
        if profile.get("input_url")
    }
