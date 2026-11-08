"""Shared-background hooks: verified overlaps between the user and a recipient.

Only facts present in BOTH the resume and the scraped profile are returned, so the
LLM gets a true hook (same school, same company, same city) instead of guessing.
Note: the BrightData profile dataset currently returns no experience history, so
past-company overlap is limited to the recipient's current company.
"""

import re

MAX_HOOKS = 3


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _mentions(haystack: str, needle: str, min_len: int) -> bool:
    n = _norm(needle)
    return len(n) >= min_len and f" {n} " in f" {haystack} "


def _schools(content: dict) -> list[str]:
    names: list[str] = []
    for item in content.get("education") or []:
        if isinstance(item, dict) and item.get("title"):
            names.append(str(item["title"]).strip())
    details = content.get("educations_details")
    if isinstance(details, str) and details.strip():
        names.append(details.strip())
    seen: set[str] = set()
    unique = []
    for name in names:
        key = _norm(name)
        if key and key not in seen:
            seen.add(key)
            unique.append(name)
    return unique


def shared_background(resume_md: str, profile: dict | None) -> list[str]:
    if not resume_md or not isinstance(profile, dict):
        return []
    resume = _norm(resume_md)
    card = profile.get("card_info") or {}
    content = profile.get("content") or {}
    hooks: list[str] = []

    for school in _schools(content):
        if _mentions(resume, school, min_len=6):
            hooks.append(f"Both of you studied at {school}.")

    company = card.get("current_company_name") or content.get("current_company_name")
    if company and _mentions(resume, str(company), min_len=3):
        hooks.append(f"Your resume mentions {company}, where they work now.")

    location = str(card.get("location") or "")
    city = location.split(",")[0].strip()
    if city and _mentions(resume, city, min_len=4):
        hooks.append(
            f"You are both connected to {city} (on your resume and their location)."
        )

    return hooks[:MAX_HOOKS]


def format_hooks(hooks: list[str]) -> str:
    return "\n".join(f"- {h}" for h in hooks) if hooks else "None found."
