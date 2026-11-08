"""The job-search profile: what to search for, confirmed by the user."""

import hashlib
import json
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.logging import get_logger
from app.core.settings import PROMPTS_DIR
from app.infra.config import load_config
from app.infra.db import connect
from app.services.jobsearch.facts import resume_facts
from app.services.structured_resume import StructuredResume

logger = get_logger(__name__)

# Adzuna's supported countries (developer.adzuna.com). Other countries can still be
# searched via Apify/LinkedIn.
ADZUNA_COUNTRIES = {
    "in"
}  # Adzuna searches India only in this app; other countries use LinkedIn
COUNTRY_NAMES = {
    "at": "Austria",
    "au": "Australia",
    "be": "Belgium",
    "br": "Brazil",
    "ca": "Canada",
    "ch": "Switzerland",
    "de": "Germany",
    "es": "Spain",
    "fr": "France",
    "gb": "United Kingdom",
    "in": "India",
    "it": "Italy",
    "mx": "Mexico",
    "nl": "Netherlands",
    "nz": "New Zealand",
    "pl": "Poland",
    "sg": "Singapore",
    "us": "United States",
    "za": "South Africa",
    "ie": "Ireland",
    "se": "Sweden",
    "dk": "Denmark",
    "fi": "Finland",
    "no": "Norway",
    "pt": "Portugal",
    "ae": "United Arab Emirates",
}
LANGUAGE_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2", "native"]
Seniority = Literal["intern", "entry", "junior", "mid", "senior"]


class Language(BaseModel):
    name: str = ""
    level: str = ""


class Clarification(BaseModel):
    question: str
    answer: str = ""


class Salary(BaseModel):
    amount: float
    currency: str = ""


class SearchProfile(BaseModel):
    titles: list[str] = Field(default_factory=list)
    seniority: Seniority = "entry"
    skills: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    company_types: list[Literal["startup", "scaleup", "enterprise", "any"]] = Field(
        default_factory=lambda: ["any"]
    )
    needs_sponsorship: bool = False
    languages: list[Language] = Field(default_factory=list)
    willing_to_relocate: bool = False
    remote: Literal["remote", "hybrid", "onsite", "any"] = "any"
    min_salary: Salary | None = None
    career_direction: str = ""
    clarifications: list[Clarification] = Field(default_factory=list)
    hide_german_required: bool = False
    # Job-type questionnaire (see preferences.QUESTIONS). Empty list = no filter.
    employment_types: list[Literal["full_time", "part_time", "contract"]] = Field(
        default_factory=list
    )
    experience_levels: list[
        Literal["internship", "entry", "associate", "mid_senior", "director"]
    ] = Field(default_factory=list)
    posted_within_days: Literal[7, 14, 30] = 30
    # Years of experience; None = computed from the resume (facts.resume_facts).
    years_experience: float | None = None
    # Hide jobs asking for clearly more experience or seniority than the user has.
    hide_above_level: bool = True

    @field_validator("titles", "skills", mode="before")
    @classmethod
    def _clean_list(cls, v):
        if not isinstance(v, list):
            return v
        seen, out = set(), []
        for item in v:
            s = str(item).strip()
            if s and s.lower() not in seen:
                seen.add(s.lower())
                out.append(s)
        return out

    @field_validator("countries", mode="before")
    @classmethod
    def _clean_countries(cls, v):
        if not isinstance(v, list):
            return v
        out = []
        for c in v:
            code = str(c).strip().lower()
            if code == "uk":
                code = "gb"
            if re.fullmatch(r"[a-z]{2}", code) and code not in out:
                out.append(code)
        return out

    def german_level(self) -> str | None:
        for lang in self.languages:
            if lang.name.strip().lower() in ("german", "deutsch"):
                return lang.level or "A1"
        return None

    def prefers_startups(self) -> bool:
        return "startup" in self.company_types and "any" not in self.company_types

    def as_text(self) -> str:
        """Text used to embed what the user is looking for."""
        parts = [
            "Target roles: " + ", ".join(self.titles),
            f"Seniority: {self.seniority}",
            "Skills: " + ", ".join(self.skills),
            self.career_direction,
        ]
        parts += [f"{c.question} {c.answer}" for c in self.clarifications if c.answer]
        return "\n".join(p for p in parts if p.strip())


class ProfileQuestion(BaseModel):
    id: str
    question: str
    options: list[str] = Field(default_factory=list)


def profile_hash(profile: SearchProfile) -> str:
    return hashlib.sha256(profile.model_dump_json().encode()).hexdigest()[:16]


def resume_hash(resume: StructuredResume) -> str:
    return hashlib.sha256(resume.model_dump_json().encode()).hexdigest()[:16]


def _parse_json(text: str) -> dict:
    cleaned = re.sub(
        r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE
    ).strip()
    return json.loads(cleaned)


def suggest(
    resume: StructuredResume, ambitions: str = ""
) -> tuple[SearchProfile, list[ProfileQuestion]]:
    """LLM proposal from the resume plus up to 3 clarifying questions."""
    from app.services.generation.llm import generate_with_fallback

    template = load_config(PROMPTS_DIR / "search_profile.yaml")["prompt"]
    ambitions_text = (
        f"The user also told us their ambitions (respect these over resume defaults):\n{ambitions}"
        if ambitions.strip()
        else ""
    )
    facts = resume_facts(resume)
    raw = generate_with_fallback(
        template.format(
            resume=resume.to_text(),
            ambitions=ambitions_text,
            facts=facts.as_prompt_text(),
        ),
        json_mode=True,
        purpose="search_profile",
    )
    data = _parse_json(raw)
    data["years_experience"] = (
        facts.years_experience
    )  # shown in the form; user can change it
    questions = [
        ProfileQuestion.model_validate(q) for q in (data.pop("questions", None) or [])
    ][:3]
    data["titles"] = (data.get("titles") or [])[:5]
    if data.get("seniority") not in ("intern", "entry", "junior", "mid", "senior"):
        data["seniority"] = "entry"
    data["company_types"] = [
        t
        for t in (data.get("company_types") or [])
        if t in ("startup", "scaleup", "enterprise", "any")
    ] or ["any"]
    if data.get("remote") not in ("remote", "hybrid", "onsite", "any"):
        data["remote"] = "any"
    if not data.get("experience_levels"):
        from app.services.jobsearch.preferences import SENIORITY_TO_EXPERIENCE

        data["experience_levels"] = SENIORITY_TO_EXPERIENCE.get(data["seniority"], [])
    return SearchProfile.model_validate(data), questions


def load() -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM search_profile WHERE id = 1").fetchone()
    if not row:
        return None
    return {
        "profile": SearchProfile.model_validate_json(row["data"]),
        "confirmed": row["confirmed_at"] is not None,
        "source_hash": row["source_hash"],
        "updated_at": row["updated_at"],
    }


def save(profile: SearchProfile, source_hash: str, confirmed: bool) -> dict:
    now = datetime.now().isoformat(timespec="seconds")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO search_profile (id, data, source_hash, confirmed_at, updated_at)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET data = excluded.data,
                source_hash = excluded.source_hash,
                confirmed_at = excluded.confirmed_at, updated_at = excluded.updated_at
            """,
            (profile.model_dump_json(), source_hash, now if confirmed else None, now),
        )
    return load()  # type: ignore[return-value]


def confirmed_profile() -> SearchProfile | None:
    state = load()
    return state["profile"] if state and state["confirmed"] else None
