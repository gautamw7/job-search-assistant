"""Facts computed from the structured resume, so the AI never has to guess them.

Used for the search questions (no asking about things the resume already says),
for the years-of-experience default, and for the "above your level" check.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime

from app.services.structured_resume import StructuredResume

MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "mär": 3,
    "apr": 4,
    "may": 5,
    "mai": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "okt": 10,
    "nov": 11,
    "dec": 12,
    "dez": 12,
}
PRESENT = {
    "present",
    "current",
    "now",
    "today",
    "ongoing",
    "heute",
    "aktuell",
    "bis heute",
}
_MONTH_YEAR = re.compile(r"([A-Za-zäÄ]{3,9})\.?\s+(\d{4})")
_YEAR = re.compile(r"(\d{4})")


@dataclass
class ResumeFacts:
    years_experience: float
    currently_employed: bool
    current_role: str
    degree_completed: bool
    highest_degree: str
    today: str

    def as_prompt_text(self) -> str:
        lines = [
            f"Today's date: {self.today}",
            f"Years of professional experience: about {self.years_experience:g}",
            "Currently employed: "
            + (f"yes, {self.current_role}" if self.currently_employed else "no"),
            "Degree: "
            + (
                f"{self.highest_degree}, completed"
                if self.degree_completed
                else f"{self.highest_degree}, in progress"
            ),
        ]
        return "\n".join(lines)


def _parse(text: str, today: date, is_end: bool) -> date | None:
    cleaned = (text or "").strip().casefold()
    if not cleaned:
        return None
    if cleaned in PRESENT:
        return today
    m = _MONTH_YEAR.search(cleaned)
    if m and m.group(1)[:3] in MONTHS:
        return date(int(m.group(2)), MONTHS[m.group(1)[:3]], 1)
    y = _YEAR.search(cleaned)
    if y:
        return date(int(y.group(1)), 12 if is_end else 1, 1)
    return None


def _months(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def _merged_months(intervals: list[tuple[date, date]]) -> int:
    """Total months covered, counting overlapping roles once."""
    total, current = 0, None
    for start, end in sorted(intervals):
        if current is None or start > current[1]:
            if current is not None:
                total += _months(*current)
            current = [start, end]
        else:
            current[1] = max(current[1], end)
    if current is not None:
        total += _months(*current)
    return total


def resume_facts(resume: StructuredResume, today: date | None = None) -> ResumeFacts:
    today = today or datetime.now().date()
    spans, current = [], None
    for role in resume.experience:
        start = _parse(role.start, today, is_end=False)
        end = _parse(role.end, today, is_end=True)
        if start is None:
            continue
        end = end or start
        end = min(end, today)
        spans.append((start, end))
        if role.end.strip().casefold() in PRESENT or end >= date(
            today.year, today.month, 1
        ):
            current = current or role
    years = round(_merged_months(spans) / 12, 1)

    degree_completed, highest = False, "Degree"
    for edu in resume.education:
        end = _parse(edu.end, today, is_end=True)
        if edu.degree:
            highest = f"{edu.degree}{' ' + edu.field if edu.field else ''}"
        if end is not None and end.year <= today.year:
            degree_completed = True

    return ResumeFacts(
        years_experience=years,
        currently_employed=current is not None,
        current_role=f"{current.title} at {current.company}" if current else "",
        degree_completed=degree_completed,
        highest_degree=highest.strip(),
        today=today.isoformat(),
    )


# ---- job requirements read from the posting ---------------------------------------

_RANGE = re.compile(
    r"(\d{1,2})\s*(?:[-–]|to|bis)\s*\d{1,2}\s*(?:years?|yrs?|jahre[n]?)\b"
)
_EXPERIENCE_CONTEXT = r"(?:experience|berufserfahrung|professional|praxis|background)"
_YEARS_PATTERNS = [
    re.compile(r"(\d{1,2})\s*\+\s*(?:years?|yrs?|jahre[n]?)\b"),
    re.compile(
        r"(?:at least|minimum of|minimum|min\.?|mindestens|min)\s*(\d{1,2})\s*(?:years?|yrs?|jahre[n]?)"
    ),
    re.compile(
        rf"(\d{{1,2}})\s*(?:years?|yrs?|jahre[n]?)\s*(?:of\s+)?{_EXPERIENCE_CONTEXT}"
    ),
]


def years_required(text: str | None) -> int | None:
    """The experience a posting asks for, or None.

    '5+ years' -> 5, '3-5 years' -> 3 (the lower bound is what's required),
    'mindestens 3 Jahre Berufserfahrung' -> 3.
    """
    if not text:
        return None
    lowered = text.casefold()
    found = [int(m.group(1)) for m in _RANGE.finditer(lowered)]
    lowered = _RANGE.sub(" ", lowered)  # so the upper bound isn't read as a requirement
    found += [
        int(m.group(1))
        for pattern in _YEARS_PATTERNS
        for m in pattern.finditer(lowered)
    ]
    found = [y for y in found if 0 < y <= 30]
    return max(found) if found else None


def with_facts(profile, resume: StructuredResume | None):
    """The profile with years_experience filled from the resume when not set by the user."""
    if profile is None or profile.years_experience is not None or resume is None:
        return profile
    return profile.model_copy(
        update={"years_experience": resume_facts(resume).years_experience}
    )
