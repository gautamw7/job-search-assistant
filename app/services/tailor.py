"""Tailored resumes: LLM selection/rewording, then hard rule checks, then a fact check.

The LLM is asked to only select, reorder and reword. That instruction is not trusted:
``enforce_rules`` forces identifying fields back to the base resume, removes skills and
technologies that aren't in it, and flags numbers that don't appear in it. The fact
checker then compares the reworded text against the base resume.
"""

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from app.core.logging import get_logger
from app.core.settings import DATA_DIR, PROMPTS_DIR
from app.infra.config import load_config
from app.infra.db import connect
from app.services import latex
from app.services.factcheck import fact_check_resume
from app.services.jobsearch import store as job_store
from app.services.jobsearch.profile import confirmed_profile, resume_hash
from app.services.structured_resume import StructuredResume, confirmed_resume

logger = get_logger(__name__)

JOB_DESC_CHARS = 6000


class TailorError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9+#]+", " ", (text or "").casefold()).strip()


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?", text or ""))


def _match(items: list, key) -> dict:
    return {key(i): i for i in items if key(i)}


def enforce_rules(
    base: StructuredResume, tailored: StructuredResume
) -> tuple[StructuredResume, list[str]]:
    """Return a copy that can't contain new facts, plus notes on what was removed."""
    notes: list[str] = []
    out = tailored.model_copy(deep=True)
    out.contact = base.contact.model_copy(deep=True)
    out.languages = [lang.model_copy() for lang in base.languages]

    # Experience: only roles from the base, with their real title/company/dates.
    base_exp = _match(base.experience, lambda x: (_norm(x.company), _norm(x.title)))
    by_company: dict[str, list] = {}
    for x in base.experience:
        by_company.setdefault(_norm(x.company), []).append(x)
    kept = []
    for x in out.experience:
        src = base_exp.get((_norm(x.company), _norm(x.title)))
        if src is None and len(by_company.get(_norm(x.company), [])) == 1:
            src = by_company[_norm(x.company)][0]
        if src is None:
            notes.append(
                f"Removed a role not in your base resume: {x.title} at {x.company}"
            )
            continue
        x.title, x.company, x.location, x.start, x.end = (
            src.title,
            src.company,
            src.location,
            src.start,
            src.end,
        )
        x.bullets = x.bullets or list(src.bullets)
        kept.append(x)
    out.experience = kept

    # Education: only base schools, identifying fields from the base.
    base_edu = _match(base.education, lambda e: _norm(e.institution))
    kept = []
    for e in out.education:
        src = base_edu.get(_norm(e.institution))
        if src is None:
            notes.append(f"Removed a school not in your base resume: {e.institution}")
            continue
        kept.append(
            src.model_copy(update={"highlights": e.highlights or src.highlights})
        )
    out.education = kept

    # Projects: base projects only; technologies limited to what that project lists.
    base_proj = _match(base.projects, lambda p: _norm(p.name))
    kept = []
    for p in out.projects:
        src = base_proj.get(_norm(p.name))
        if src is None:
            notes.append(f"Removed a project not in your base resume: {p.name}")
            continue
        allowed = {_norm(t) for t in src.tech}
        extra = [t for t in p.tech if _norm(t) not in allowed]
        if extra:
            notes.append(
                f"Removed technologies not listed for {src.name}: {', '.join(extra)}"
            )
        p.tech = [t for t in p.tech if _norm(t) in allowed] or list(src.tech)
        p.name, p.link = src.name, src.link
        p.bullets = p.bullets or list(src.bullets)
        kept.append(p)
    out.projects = kept

    # Skills: only skills/technologies that appear somewhere in the base resume.
    allowed_skills = {_norm(i) for s in base.skills for i in s.items} | {
        _norm(t) for p in base.projects for t in p.tech
    }
    removed = []
    for group in out.skills:
        removed += [i for i in group.items if _norm(i) not in allowed_skills]
        group.items = [i for i in group.items if _norm(i) in allowed_skills]
    out.skills = [g for g in out.skills if g.items]
    if removed:
        notes.append(
            f"Removed skills not in your base resume: {', '.join(dict.fromkeys(removed))}"
        )

    base_certs = {_norm(c): c for c in base.certifications}
    unknown = [c for c in out.certifications if _norm(c) not in base_certs]
    if unknown:
        notes.append(
            f"Removed certifications not in your base resume: {', '.join(unknown)}"
        )
    out.certifications = [
        base_certs[_norm(c)] for c in out.certifications if _norm(c) in base_certs
    ]

    # Numbers are the easiest thing for a model to invent; flag any that are new.
    base_numbers = _numbers(base.model_dump_json())
    prose = (
        [out.summary]
        + [b for x in out.experience for b in x.bullets]
        + [b for p in out.projects for b in p.bullets]
    )
    new_numbers = sorted({n for text in prose for n in _numbers(text)} - base_numbers)
    if new_numbers:
        notes.append(
            f"Check these numbers, they are not in your base resume: {', '.join(new_numbers)}"
        )
    return out, notes


def _parse_json(text: str) -> dict:
    cleaned = re.sub(
        r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE
    ).strip()
    return json.loads(cleaned)


def _row(row) -> dict:
    return {
        "id": row["id"],
        "job_id": row["job_id"],
        "job_title": row["job_title"],
        "company": row["company"],
        "resume": json.loads(row["data"]),
        "changes": json.loads(row["changes"]),
        "keywords": json.loads(row["keywords"]),
        "guard_notes": json.loads(row["guard_notes"]),
        "fact_check": json.loads(row["fact_check"]) if row["fact_check"] else None,
        "has_pdf": bool(row["pdf_path"]) and Path(row["pdf_path"]).exists(),
        "pdf_compiled_at": row["pdf_compiled_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get(tailored_id: str) -> dict:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM tailored_resumes WHERE id = ?", (tailored_id,)
        ).fetchone()
    if not row:
        raise LookupError("Tailored resume not found")
    return _row(row)


def list_for_job(job_id: str | None = None) -> list[dict]:
    with connect() as conn:
        if job_id:
            rows = conn.execute(
                "SELECT * FROM tailored_resumes WHERE job_id = ? ORDER BY created_at DESC",
                (job_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tailored_resumes ORDER BY created_at DESC"
            ).fetchall()
    return [_row(r) for r in rows]


def create(job_id: str) -> dict:
    base = confirmed_resume()
    if base is None:
        raise TailorError("Confirm your structured resume first (Resume tab).")
    jobs = job_store.get_jobs([job_id])
    if not jobs:
        raise LookupError("Job not found")
    job = jobs[0]
    profile = confirmed_profile()

    from app.services.generation.llm import generate_with_fallback

    template = load_config(PROMPTS_DIR / "tailor_resume.yaml")["prompt"]
    raw = generate_with_fallback(
        template.format(
            job_title=job["title"],
            company=job["company"],
            job_description=(job["description"] or "")[:JOB_DESC_CHARS],
            career_direction=(profile.career_direction if profile else "")
            or "not specified",
            base_resume=base.model_dump_json(indent=1),
        ),
        json_mode=True,
        purpose="tailor_resume",
    )
    try:
        data = _parse_json(raw)
        proposed = StructuredResume.model_validate(data.get("resume") or {})
    except Exception as e:
        raise TailorError(f"The AI returned an unusable resume: {e}") from e

    tailored, notes = enforce_rules(base, proposed)
    checked = fact_check_resume(tailored.to_text(), base.to_text())
    now = _now()
    record_id = uuid.uuid4().hex[:16]
    with connect() as conn:
        conn.execute(
            """INSERT INTO tailored_resumes (id, job_id, job_title, company, data, changes, keywords,
               guard_notes, fact_check, base_hash, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                record_id,
                job_id,
                job["title"],
                job["company"],
                tailored.model_dump_json(),
                json.dumps([str(c)[:200] for c in (data.get("changes") or [])][:12]),
                json.dumps([str(k)[:60] for k in (data.get("keywords") or [])][:20]),
                json.dumps(notes),
                json.dumps(checked),
                resume_hash(base),
                now,
                now,
            ),
        )
    logger.info(
        "tailored resume created id=%s job=%s notes=%s", record_id, job_id, len(notes)
    )
    return get(record_id)


def update(tailored_id: str, resume: StructuredResume, recheck: bool = False) -> dict:
    """Save the user's edits. Rules are re-applied; the PDF must be rebuilt."""
    base = confirmed_resume()
    if base is None:
        raise TailorError("Confirm your structured resume first (Resume tab).")
    current = get(tailored_id)
    tailored, notes = enforce_rules(base, resume)
    checked = (
        fact_check_resume(tailored.to_text(), base.to_text())
        if recheck
        else current["fact_check"]
    )
    with connect() as conn:
        conn.execute(
            """UPDATE tailored_resumes SET data = ?, guard_notes = ?, fact_check = ?, pdf_path = NULL,
               pdf_compiled_at = NULL, updated_at = ? WHERE id = ?""",
            (
                tailored.model_dump_json(),
                json.dumps(notes),
                json.dumps(checked),
                _now(),
                tailored_id,
            ),
        )
    return get(tailored_id)


def delete(tailored_id: str) -> None:
    record = get(tailored_id)
    with connect() as conn:
        row = conn.execute(
            "SELECT pdf_path FROM tailored_resumes WHERE id = ?", (tailored_id,)
        ).fetchone()
        conn.execute("DELETE FROM tailored_resumes WHERE id = ?", (tailored_id,))
    if row and row["pdf_path"]:
        Path(row["pdf_path"]).unlink(missing_ok=True)
    logger.info("tailored resume deleted id=%s job=%s", tailored_id, record["job_id"])


def tex_for(tailored_id: str) -> str:
    return latex.render_tex(StructuredResume.model_validate(get(tailored_id)["resume"]))


def _pdf_dir() -> Path:
    path = DATA_DIR / "tailored"
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_pdf(tailored_id: str) -> dict:
    pdf, compiler = latex.compile_pdf(tex_for(tailored_id))
    path = _pdf_dir() / f"{tailored_id}.pdf"
    path.write_bytes(pdf)
    with connect() as conn:
        conn.execute(
            "UPDATE tailored_resumes SET pdf_path = ?, pdf_compiled_at = ? WHERE id = ?",
            (str(path), _now(), tailored_id),
        )
    return {**get(tailored_id), "compiler": compiler}


def pdf_path(tailored_id: str) -> Path:
    record = get(tailored_id)
    with connect() as conn:
        row = conn.execute(
            "SELECT pdf_path FROM tailored_resumes WHERE id = ?", (tailored_id,)
        ).fetchone()
    if not record["has_pdf"]:
        raise LookupError("Build the PDF first.")
    return Path(row["pdf_path"])


def export_filename(tailored_id: str, ext: str) -> str:
    record = get(tailored_id)
    name = record["resume"].get("contact", {}).get("name") or "Resume"
    parts = [name, record["company"] or record["job_title"]]
    slug = "_".join(re.sub(r"[^A-Za-z0-9]+", "-", p).strip("-") for p in parts if p)
    return f"{slug or 'resume'}.{ext}"


def export_to_downloads(tailored_id: str, kind: str) -> Path:
    """Write the PDF or .tex into the user's Downloads folder (works in the desktop app,
    where browser-style downloads are unreliable)."""
    downloads = Path.home() / "Downloads"
    target_dir = downloads if downloads.is_dir() else DATA_DIR / "exports"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / export_filename(tailored_id, kind)
    if kind == "pdf":
        target.write_bytes(pdf_path(tailored_id).read_bytes())
    else:
        target.write_text(tex_for(tailored_id), encoding="utf-8")
    return target
