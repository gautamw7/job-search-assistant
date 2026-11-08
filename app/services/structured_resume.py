"""Structured base resume: the single source of truth for tailoring and LaTeX.

Built once from the parsed Markdown by an LLM (told to copy, not invent), then
reviewed and edited by the user. It records the hash of the Markdown it came from,
so uploading a new resume marks it stale instead of silently diverging.
"""

import hashlib
import json
import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.logging import get_logger
from app.core.settings import PROMPTS_DIR
from app.infra.config import load_config
from app.infra.db import connect

logger = get_logger(__name__)


def _strip(v):
    return v.strip() if isinstance(v, str) else v


class _Clean(BaseModel):
    """Trim strings and drop empty strings from string lists."""

    @field_validator("*", mode="before")
    @classmethod
    def _tidy(cls, v):
        if v is None:
            return v
        if isinstance(v, list):
            v = [_strip(x) for x in v]
            return [x for x in v if x not in ("", None)]
        return _strip(v)


class Contact(_Clean):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    links: list[str] = Field(default_factory=list)


class Education(_Clean):
    institution: str = ""
    degree: str = ""
    field: str = ""
    location: str = ""
    start: str = ""
    end: str = ""
    grade: str = ""
    highlights: list[str] = Field(default_factory=list)


class Experience(_Clean):
    title: str = ""
    company: str = ""
    location: str = ""
    start: str = ""
    end: str = ""
    bullets: list[str] = Field(default_factory=list)


class Project(_Clean):
    name: str = ""
    tech: list[str] = Field(default_factory=list)
    link: str = ""
    bullets: list[str] = Field(default_factory=list)


class SkillGroup(_Clean):
    category: str = ""
    items: list[str] = Field(default_factory=list)


class Language(_Clean):
    name: str = ""
    level: str = ""


class StructuredResume(_Clean):
    contact: Contact = Field(default_factory=Contact)
    summary: str = ""
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    skills: list[SkillGroup] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)

    @field_validator(
        "education", "experience", "projects", "skills", "languages", mode="before"
    )
    @classmethod
    def _drop_empty_items(cls, v):
        if not isinstance(v, list):
            return v
        return [x for x in v if not (isinstance(x, dict) and not any(x.values()))]

    def to_text(self) -> str:
        """Plain-text rendering used as a fact source (e.g. for the fact checker)."""
        lines = [self.contact.name, self.contact.location, self.summary]
        for e in self.education:
            lines.append(
                f"{e.degree} {e.field} — {e.institution} ({e.start}–{e.end}) {e.grade}"
            )
            lines += e.highlights
        for x in self.experience:
            lines.append(f"{x.title} at {x.company}, {x.location} ({x.start}–{x.end})")
            lines += x.bullets
        for p in self.projects:
            lines.append(f"Project: {p.name} [{', '.join(p.tech)}]")
            lines += p.bullets
        for s in self.skills:
            lines.append(f"{s.category}: {', '.join(s.items)}")
        lines += self.certifications
        lines += [f"{lang.name} ({lang.level})" for lang in self.languages]
        return "\n".join(line for line in lines if line and line.strip())


def markdown_hash(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _parse_json(text: str) -> dict:
    cleaned = re.sub(
        r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE
    ).strip()
    return json.loads(cleaned)


def convert_markdown(markdown: str) -> StructuredResume:
    """LLM extraction of the Markdown resume into the structured schema."""
    from app.services.generation.llm import generate_with_fallback

    template = load_config(PROMPTS_DIR / "structure_resume.yaml")["prompt"]
    raw = generate_with_fallback(
        template.format(resume=markdown), json_mode=True, purpose="structure_resume"
    )
    return StructuredResume.model_validate(_parse_json(raw))


def load() -> dict | None:
    """{"resume", "confirmed", "updated_at", "source_hash"} or None."""
    with connect() as conn:
        row = conn.execute("SELECT * FROM base_resume WHERE id = 1").fetchone()
    if not row:
        return None
    return {
        "resume": StructuredResume.model_validate_json(row["data"]),
        "confirmed": row["confirmed_at"] is not None,
        "confirmed_at": row["confirmed_at"],
        "updated_at": row["updated_at"],
        "source_hash": row["source_hash"],
    }


def save(resume: StructuredResume, source_hash: str, confirmed: bool) -> dict:
    now = _now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO base_resume (id, data, source_hash, confirmed_at, updated_at)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                data = excluded.data, source_hash = excluded.source_hash,
                confirmed_at = excluded.confirmed_at, updated_at = excluded.updated_at
            """,
            (resume.model_dump_json(), source_hash, now if confirmed else None, now),
        )
    logger.info("structured resume saved confirmed=%s", confirmed)
    return load()  # type: ignore[return-value]


def confirmed_resume() -> StructuredResume | None:
    """The reviewed resume, or None if it doesn't exist or isn't confirmed yet."""
    state = load()
    return state["resume"] if state and state["confirmed"] else None
