"""Phase 3: rule checks, LaTeX rendering/compiling and the tailored-resume API."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.core.settings import DATA_DIR
from app.infra import db
from app.services import latex
from app.services.jobsearch import store as job_store
from app.services.jobsearch.sources.base import JobPosting
from app.services.structured_resume import StructuredResume
from app.services.structured_resume import save as save_resume
from app.services.tailor import enforce_rules

client = TestClient(app)

BASE = StructuredResume.model_validate(
    {
        "contact": {
            "name": "Alex Rivera",
            "email": "alex@example.com",
            "links": ["github.com/alex"],
        },
        "summary": "Data scientist.",
        "experience": [
            {
                "title": "ML Engineer Intern",
                "company": "Acme",
                "start": "Feb 2026",
                "end": "Aug 2026",
                "bullets": ["Built ranking models in PyTorch that lifted CTR by 4%"],
            }
        ],
        "projects": [
            {
                "name": "RAG assistant",
                "tech": ["Python", "Qdrant"],
                "bullets": ["Answered questions"],
            }
        ],
        "skills": [{"category": "Languages", "items": ["Python", "SQL"]}],
        "education": [
            {
                "institution": "VIT Pune",
                "degree": "B.Tech",
                "start": "2022",
                "end": "2026",
            }
        ],
        "certifications": ["AWS ML Specialty"],
        "languages": [{"name": "German", "level": "A2"}],
    }
)


@pytest.fixture(autouse=True)
def fresh_db():
    (DATA_DIR / "app.db").unlink(missing_ok=True)
    db._migrated_paths.clear()
    (DATA_DIR / "settings.json").unlink(missing_ok=True)
    yield


def test_rules_strip_invented_facts_and_restore_identifiers():
    proposed = BASE.model_copy(deep=True)
    proposed.contact.email = "fake@x.com"
    proposed.experience[0].title = "Senior ML Engineer"  # promoted itself
    proposed.experience[0].start = "2020"
    proposed.experience[0].bullets = [
        "Led a team of 12 to ship ranking models with PyTorch, lifting CTR by 4%"
    ]
    proposed.experience.append(
        proposed.experience[0].model_copy(update={"company": "Google", "title": "SWE"})
    )
    proposed.projects[0].tech = ["Python", "Kubernetes"]
    proposed.skills[0].items = ["Python", "Rust", "SQL"]
    proposed.certifications = ["AWS ML Specialty", "CKA"]
    proposed.languages = [{"name": "German", "level": "C1"}]
    proposed.education[0].degree = "M.Tech"

    out, notes = enforce_rules(
        BASE, StructuredResume.model_validate(proposed.model_dump())
    )
    assert out.contact.email == "alex@example.com"
    assert [(x.title, x.company, x.start) for x in out.experience] == [
        ("ML Engineer Intern", "Acme", "Feb 2026")
    ]
    assert out.projects[0].tech == ["Python"]
    assert out.skills[0].items == ["Python", "SQL"]
    assert out.certifications == ["AWS ML Specialty"]
    assert out.languages[0].level == "A2" and out.education[0].degree == "B.Tech"
    joined = " | ".join(notes)
    for expected in ("Google", "Kubernetes", "Rust", "CKA", "12"):
        assert expected in joined, (expected, joined)
    assert "4" not in [
        n for n in joined.split("numbers")[-1].split(", ")
    ]  # 4% exists in base


def test_escape_handles_every_special_character():
    assert latex.escape("50% of R&D_team #1 {x} ~ ^ $5 \\ <a>") == (
        r"50\% of R\&D\_team \#1 \{x\} \textasciitilde{} \textasciicircum{} \$5 \textbackslash{} \textless{}a\textgreater{}"
    )
    tex = latex.render_tex(BASE)
    assert (
        r"\section*{Experience}" in tex
        and "Feb 2026 -- Aug 2026" in tex
        and r"\end{document}" in tex
    )


@pytest.mark.skipif(latex.find_compiler() is None, reason="no LaTeX compiler installed")
def test_real_compile_produces_a_pdf():
    pdf, name = latex.compile_pdf(latex.render_tex(BASE))
    assert pdf.startswith(b"%PDF") and name in ("xelatex", "pdflatex", "tectonic")


def _setup_job():
    save_resume(BASE, "h", confirmed=True)
    [job_id] = job_store.upsert_postings(
        [
            JobPosting(
                "apify",
                "1",
                "ML Engineer",
                "TinyAI",
                "Berlin",
                "de",
                "PyTorch ranking, Python, SQL",
                False,
                "u",
            )
        ]
    )
    return job_id


def test_create_edit_build_export_delete(tmp_path):
    job_id = _setup_job()
    proposed = BASE.model_copy(deep=True)
    proposed.skills[0].items = ["Python", "SQL", "Spark"]
    llm_answer = json.dumps(
        {
            "resume": proposed.model_dump(),
            "changes": ["Moved ranking work first"],
            "keywords": ["PyTorch"],
        }
    )
    with patch(
        "app.services.generation.llm.generate_with_fallback",
        side_effect=[llm_answer, '{"issues": []}'],
    ):
        r = client.post("/tailored", json={"job_id": job_id})
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["company"] == "TinyAI" and t["fact_check"]["status"] == "pass"
    assert any("Spark" in n for n in t["guard_notes"]) and "Spark" not in json.dumps(
        t["resume"]["skills"]
    )
    assert [x["id"] for x in client.get(f"/tailored?job_id={job_id}").json()] == [
        t["id"]
    ]

    edited = t["resume"] | {"summary": "ML engineer focused on ranking."}
    r = client.put(f"/tailored/{t['id']}", json=edited)
    assert (
        r.json()["resume"]["summary"] == "ML engineer focused on ranking."
        and r.json()["has_pdf"] is False
    )

    assert "\\documentclass" in client.get(f"/tailored/{t['id']}/tex").text
    assert client.get(f"/tailored/{t['id']}/pdf").status_code == 404  # not built yet
    with patch(
        "app.services.latex.compile_pdf", return_value=(b"%PDF-1.7 fake", "tectonic")
    ):
        built = client.post(f"/tailored/{t['id']}/pdf").json()
    assert built["has_pdf"] and built["compiler"] == "tectonic"
    assert client.get(f"/tailored/{t['id']}/pdf").content.startswith(b"%PDF")

    (tmp_path / "Downloads").mkdir()
    with patch("app.services.tailor.Path.home", return_value=tmp_path):
        path = Path(
            client.post(f"/tailored/{t['id']}/export", json={"kind": "pdf"}).json()[
                "path"
            ]
        )
    assert (
        path.parent == tmp_path / "Downloads" and path.name == "Alex-Rivera_TinyAI.pdf"
    )

    assert client.delete(f"/tailored/{t['id']}").json()["deleted"]
    assert client.get(f"/tailored/{t['id']}").status_code == 404


def test_compile_errors_and_missing_inputs_are_reported():
    assert client.post("/tailored", json={"job_id": "nope"}).status_code in (400, 404)
    job_id = _setup_job()
    assert client.post("/tailored", json={"job_id": "nope"}).status_code == 404
    with patch(
        "app.services.generation.llm.generate_with_fallback", return_value="not json"
    ):
        assert client.post("/tailored", json={"job_id": job_id}).status_code == 400
    with (
        patch("app.services.latex.find_compiler", return_value=None),
        pytest.raises(latex.CompileError, match="No LaTeX compiler"),
    ):
        latex.compile_pdf("x")
