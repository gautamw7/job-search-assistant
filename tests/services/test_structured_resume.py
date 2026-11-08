import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.app import app
from app.core.settings import RESUME_MD
from app.services import structured_resume as sr

client = TestClient(app)

LLM_JSON = json.dumps(
    {
        "contact": {
            "name": " Alex Rivera ",
            "email": "alex@example.com",
            "phone": "",
            "location": "Pune",
            "links": ["", "github.com/alex"],
        },
        "summary": "",
        "education": [
            {
                "institution": "VIT Pune",
                "degree": "B.Tech",
                "field": "CS",
                "start": "2022",
                "end": "2026",
            },
            {"institution": "", "degree": "", "field": ""},
        ],
        "experience": [
            {
                "title": "Data Scientist Intern",
                "company": "Syngenta",
                "start": "Feb 2026",
                "end": "Aug 2026",
                "bullets": ["Built XGBoost demand model", ""],
            }
        ],
        "projects": [],
        "skills": [{"category": "Languages", "items": ["Python", "SQL"]}],
        "certifications": [],
        "languages": [],
    }
)


def test_validation_trims_and_drops_empties():
    r = sr.StructuredResume.model_validate(json.loads(LLM_JSON))
    assert r.contact.name == "Alex Rivera"
    assert r.contact.links == ["github.com/alex"]
    assert len(r.education) == 1  # blank item dropped
    assert r.experience[0].bullets == ["Built XGBoost demand model"]
    assert "Syngenta" in r.to_text()


def test_convert_save_confirm_and_stale_flow():
    RESUME_MD.parent.mkdir(parents=True, exist_ok=True)
    RESUME_MD.write_text(
        "# Alex\nalex@example.com\nExperience: Syngenta intern", encoding="utf-8"
    )
    with patch(
        "app.services.generation.llm.generate_with_fallback", return_value=LLM_JSON
    ):
        r = client.post("/resume/structured/convert")
    assert r.status_code == 200
    body = r.json()
    assert body["confirmed"] is False and body["stale"] is False
    assert sr.confirmed_resume() is None  # not usable until reviewed

    edited = body["resume"]
    edited["summary"] = "Entry-level data scientist."
    r = client.put("/resume/structured", json=edited)
    assert r.status_code == 200 and r.json()["confirmed"] is True
    assert sr.confirmed_resume().summary == "Entry-level data scientist."

    RESUME_MD.write_text("# Alex\nnew resume uploaded", encoding="utf-8")
    assert client.get("/resume/structured").json()["stale"] is True


def test_empty_resume_rejected_and_convert_errors_reported():
    assert client.put("/resume/structured", json={}).status_code == 400
    RESUME_MD.write_text("# Alex", encoding="utf-8")
    with patch(
        "app.services.generation.llm.generate_with_fallback", return_value="not json"
    ):
        assert client.post("/resume/structured/convert").status_code == 502
