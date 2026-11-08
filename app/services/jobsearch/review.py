"""LLM re-rank of the shortlist, in small batches to stay inside free-tier limits."""

import json
import re

from app.core.logging import get_logger
from app.core.settings import PROMPTS_DIR
from app.infra.config import load_config
from app.services.jobsearch.profile import SearchProfile

logger = get_logger(__name__)

BATCH = 5
DESC_CHARS = 3500
_ENUMS = {
    "german_required": {"yes", "no", "unclear"},
    "sponsorship": {"yes", "no", "unclear"},
    "company_kind": {"startup", "scaleup", "enterprise", "unknown"},
}


def _profile_text(p: SearchProfile) -> str:
    lines = [
        f"Target titles: {', '.join(p.titles)}",
        f"Seniority: {p.seniority}",
        f"Countries (preferred first): {', '.join(p.countries)}",
        f"Company types: {', '.join(p.company_types)}",
        f"Needs visa sponsorship: {'yes' if p.needs_sponsorship else 'no'}",
        "Languages: "
        + ", ".join(f"{lang.name} {lang.level}".strip() for lang in p.languages),
        f"Career direction: {p.career_direction}",
    ]
    lines += [f"Q: {c.question} A: {c.answer}" for c in p.clarifications if c.answer]
    return "\n".join(lines)


def _clean(review: dict) -> dict:
    out = {
        "fit": max(0, min(100, int(review.get("fit", 0))))
        if str(review.get("fit", "")).strip()
        else None,
        "reasons": [str(r)[:200] for r in (review.get("reasons") or [])][:3],
        "missing_skills": [str(s)[:60] for s in (review.get("missing_skills") or [])][
            :4
        ],
        "german_level": str(review.get("german_level") or "").strip()[:10],
    }
    for key, allowed in _ENUMS.items():
        value = str(review.get(key, "")).strip().lower()
        out[key] = (
            value
            if value in allowed
            else ("unknown" if key == "company_kind" else "unclear")
        )
    return out


def review_jobs(
    jobs: list[dict], profile: SearchProfile, resume_text: str
) -> dict[str, dict]:
    """{job_id: review}. Batches that fail are skipped (the job keeps its factor score)."""
    from app.services.generation.llm import generate_with_fallback

    template = load_config(PROMPTS_DIR / "job_review.yaml")["prompt"]
    reviews: dict[str, dict] = {}
    for i in range(0, len(jobs), BATCH):
        batch = jobs[i : i + BATCH]
        jobs_text = "\n\n".join(
            f"[id: {j['id']}]\n{j['title']} — {j['company']} ({j['location']})"
            + (
                f"\nCompany size: {j['company_size']} employees"
                if j.get("company_size")
                else ""
            )
            + f"\n{(j.get('description') or '')[:DESC_CHARS]}"
            for j in batch
        )
        try:
            raw = generate_with_fallback(
                template.format(
                    profile=_profile_text(profile), resume=resume_text, jobs=jobs_text
                ),
                json_mode=True,
                purpose="job_review",
            )
            cleaned = re.sub(
                r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE
            ).strip()
            data = json.loads(cleaned)
            items = data.get("reviews", []) if isinstance(data, dict) else data
            wanted = {j["id"] for j in batch}
            for item in items:
                if isinstance(item, dict) and item.get("id") in wanted:
                    reviews[item["id"]] = _clean(item)
        except Exception as e:
            logger.warning("job review batch failed: %s", e)
            if "free-tier limit" in str(e):
                raise
    return reviews
