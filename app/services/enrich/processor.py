"""Internal: enrich processing — extract, classify, markdown."""

import re

from app.services.logger import get_logger

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
    "current_company_name",
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
    r"\bwe are looking for\b",
    r"\bis looking for\b",
    r"\blooking for\b",
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
        if k not in CARD_FIELDS and k not in CONTENT_FIELDS and k not in {"activity", "people_also_viewed"}
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


def content_to_markdown(content: dict) -> str:
    md_parts: list[str] = []
    for key, value in content.items():
        md_parts.append(f"## {key}")
        if value is None:
            md_parts.append("None")
        elif isinstance(value, list):
            if not value:
                md_parts.append("None")
            else:
                for item in value:
                    if isinstance(item, dict):
                        for k2, v2 in item.items():
                            md_parts.append(f"### {k2}: {v2}")
                        md_parts.append("")
                    else:
                        md_parts.append(f"- {item}")
        elif isinstance(value, dict):
            for k2, v2 in value.items():
                md_parts.append(f"### {k2}: {v2}")
        else:
            md_parts.append(f"{value}")
        md_parts.append("")
    return "\n".join(md_parts).strip()


def map_enrich_data_by_url(results: list) -> dict:
    return {
        profile["input_url"]: process_enrich_data(profile)
        for profile in results
        if profile.get("input_url")
    }
