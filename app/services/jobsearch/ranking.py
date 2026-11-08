"""Weighted job score. Each factor is 0..1 and shown to the user as a breakdown."""

import re
from datetime import datetime

from app.services.jobsearch.profile import SearchProfile

WEIGHTS = {
    "similarity": 0.30,
    "title": 0.20,
    "skills": 0.15,
    "seniority": 0.10,
    "location": 0.10,
    "startup": 0.10,
    "recency": 0.05,
}
SENIORITY_ORDER = ["intern", "entry", "junior", "mid", "senior"]
_SENIORITY_HINTS = [
    ("intern", r"\b(intern|internship|praktik\w*|werkstudent|working student)\b"),
    ("entry", r"\b(entry|graduate|trainee|fresher|new grad|associate|einstieg\w*)\b"),
    ("junior", r"\bjunior|jr\.?\b"),
    ("senior", r"\b(senior|sr\.?|lead|principal|staff|head|director|manager)\b"),
    ("mid", r"\b(mid|intermediate|ii|iii)\b"),
]
LANG_ORDER = ["a1", "a2", "b1", "b2", "c1", "c2", "native"]


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+#]+", (text or "").casefold()))


# Rank scale used for "above your level": 0 intern, 1 entry, 2 associate/junior,
# 3 mid / mid-senior, 4 senior / lead / staff, 5 manager / director / head.
_RANK_HINTS = [
    (
        5,
        r"\b(director|vp|vice president|head of|chief|manager|leiter|leitung|teamleiter)\b",
    ),
    (4, r"\b(senior|sr\.?|staff|principal|lead|architect|expert|iii|iv)\b"),
    (3, r"\b(mid|intermediate|ii)\b"),
    (2, r"\b(junior|jr\.?|associate|assistant)\b"),
    (1, r"\b(entry|graduate|trainee|fresher|new grad|einstieg)\b"),
    (0, r"\b(intern|internship|praktik\w*|werkstudent|working student)\b"),
]
_BOARD_RANK = {
    "internship": 0,
    "entry level": 1,
    "associate": 2,
    "mid-senior level": 3,
    "director": 5,
}  # "executive" is too vague to trust (job boards use it for entry roles too); the title decides
_USER_RANK = {
    "internship": 0,
    "entry": 1,
    "associate": 2,
    "mid_senior": 3,
    "director": 5,
}
ABOVE_SCORE_CAP = 30.0
ABOVE_YEARS_MARGIN = 1.5


def job_rank(job: dict) -> int | None:
    """Seniority rank of a job: the job board's field when it has one, else the title."""
    board = str(job.get("seniority") or "").strip().casefold()
    if board in _BOARD_RANK:
        return _BOARD_RANK[board]
    title = str(job.get("title") or "").casefold()
    for rank, pattern in _RANK_HINTS:
        if re.search(pattern, title):
            return rank
    return None


def user_rank(profile: SearchProfile) -> int:
    """Highest level the user is looking for (their choices, or their years)."""
    chosen = [_USER_RANK[e] for e in profile.experience_levels if e in _USER_RANK]
    if chosen:
        return max(chosen)
    years = profile.years_experience or 0.0
    return 1 if years < 2 else (2 if years < 4 else 3)


def above_level(job: dict, profile: SearchProfile) -> str | None:
    """Why this job is above the user's level, or None if it isn't."""
    from app.services.jobsearch.facts import years_required

    rank = job_rank(job)
    user = user_rank(profile)
    if rank is not None and rank - user >= 2:
        return (
            "a senior role for your level" if rank < 5 else "a manager or director role"
        )
    asked = years_required(f"{job.get('title') or ''}\n{job.get('description') or ''}")
    have = profile.years_experience or 0.0
    if asked is not None and asked > have + ABOVE_YEARS_MARGIN:
        return f"asks for {asked}+ years; you have about {have:g}"
    return None


def job_seniority(job: dict) -> str | None:
    text = f"{job.get('seniority') or ''} {job.get('title') or ''}".casefold()
    for level, pattern in _SENIORITY_HINTS:
        if re.search(pattern, text):
            return level
    if "entry level" in text or "internship" in text:
        return "entry"
    return None


def title_match(job_title: str, targets: list[str]) -> float:
    jt = _words(job_title)
    best = 0.0
    for target in targets:
        tw = _words(target)
        if not tw:
            continue
        if target.casefold() in (job_title or "").casefold():
            return 1.0
        best = max(best, len(jt & tw) / len(tw))
    return round(best, 3)


def skills_match(description: str, skills: list[str]) -> float:
    if not skills:
        return 0.5
    text = (description or "").casefold()
    hits = sum(
        1
        for s in skills
        if re.search(rf"(?<![a-z0-9]){re.escape(s.casefold())}(?![a-z0-9])", text)
    )
    # Matching ~6 of your skills is already a strong signal.
    return round(min(1.0, hits / min(6, len(skills))), 3)


def seniority_fit(job: dict, wanted: str) -> float:
    level = job_seniority(job)
    if level is None:
        return 0.6
    gap = abs(SENIORITY_ORDER.index(level) - SENIORITY_ORDER.index(wanted))
    return {0: 1.0, 1: 0.6}.get(gap, 0.1)


def location_fit(job: dict, profile: SearchProfile) -> float:
    countries = profile.countries
    if job.get("country") in countries:
        base = 1.0 - 0.2 * countries.index(job["country"])
    else:
        base = 0.3
    remote = job.get("remote")
    if profile.remote != "any" and remote and remote != profile.remote:
        base -= 0.2
    return round(max(0.0, min(1.0, base)), 3)


def startup_fit(job: dict, profile: SearchProfile, max_employees: int) -> float:
    if not profile.prefers_startups():
        return 0.5
    size = job.get("company_size")
    if size is None:
        return 0.5
    if size < max_employees:
        return 1.0
    return 0.6 if size < 1000 else 0.2


def recency(job: dict, max_days: int) -> float:
    posted = job.get("posted_at")
    if not posted:
        return 0.5
    try:
        when = datetime.fromisoformat(str(posted)).replace(tzinfo=None)
    except ValueError:
        return 0.5
    days = max(0, (datetime.now() - when).days)
    return round(max(0.0, 1 - days / max_days), 3)


def company_kind(job: dict, max_employees: int) -> str | None:
    size = job.get("company_size")
    if size is None:
        return None
    return (
        "startup"
        if size < max_employees
        else ("scaleup" if size < 1000 else "enterprise")
    )


def score_jobs(
    jobs: list[dict],
    similarities: dict[str, float] | None,
    profile: SearchProfile,
    max_days: int,
    max_employees: int,
) -> list[tuple[str, float, dict]]:
    """(job_id, score 0-100, breakdown) for each job.

    Jobs above the user's level are capped at ABOVE_SCORE_CAP and carry the reason
    in ``breakdown["above_level"]``.

    ``similarities=None`` means AI matching was unavailable: the similarity weight
    is shared out across the other factors so scores stay on the same 0-100 scale.
    """
    use_similarity = similarities is not None
    sims_values = (
        [similarities.get(j["id"], 0.0) for j in jobs] if use_similarity else []
    )
    lo, hi = (min(sims_values), max(sims_values)) if sims_values else (0.0, 1.0)
    span = (hi - lo) or 1.0
    weights = dict(WEIGHTS)
    if not use_similarity:
        spare = weights.pop("similarity")
        share = spare / (sum(weights.values()) or 1.0)
        weights = {k: w + w * share for k, w in weights.items()}
    scored = []
    for job in jobs:
        breakdown = {
            "similarity": (
                round((similarities.get(job["id"], lo) - lo) / span, 3)
                if use_similarity
                else None
            ),
            "title": title_match(job["title"], profile.titles),
            "skills": skills_match(job["description"], profile.skills),
            "seniority": seniority_fit(job, profile.seniority),
            "location": location_fit(job, profile),
            "startup": startup_fit(job, profile, max_employees),
            "recency": recency(job, max_days),
        }
        score = 100 * sum(
            weights[k] * v
            for k, v in breakdown.items()
            if v is not None and k in weights
        )
        reason = above_level(job, profile)
        breakdown["above_level"] = reason
        if reason:
            score = min(score, ABOVE_SCORE_CAP)
        scored.append((job["id"], round(score, 1), breakdown))
    return scored


def language_gap(required: str | None, have: str | None) -> bool:
    """True if the job's German requirement is above the user's level."""
    if not required:
        return False
    req = required.strip().casefold()
    if req not in LANG_ORDER:
        req = "b2"  # "fluent German" without a level ≈ B2+
    have_level = (have or "").strip().casefold()
    if have_level not in LANG_ORDER:
        return True
    return LANG_ORDER.index(have_level) < LANG_ORDER.index(req)


def apply_review(
    base_score: float, breakdown: dict, review: dict, profile: SearchProfile
) -> tuple[float, dict]:
    """Blend the LLM fit with the factor score and apply Germany/visa penalties."""
    fit = review.get("fit")
    score = (
        base_score
        if not isinstance(fit, (int, float))
        else 0.5 * base_score + 0.5 * float(fit)
    )
    penalties = {}
    if review.get("german_required") == "yes" and language_gap(
        review.get("german_level"), profile.german_level()
    ):
        penalties["german"] = -25
    if profile.needs_sponsorship and review.get("sponsorship") == "no":
        penalties["sponsorship"] = -20
    score += sum(penalties.values())
    return round(max(0.0, min(100.0, score)), 1), {
        **breakdown,
        "llm_fit": fit,
        "penalties": penalties,
    }
