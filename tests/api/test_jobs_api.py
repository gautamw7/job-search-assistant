import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.app import app
from app.core.settings import DATA_DIR, ENRICH_DATA, GENERATED_MESSAGES
from app.infra import db
from app.services.jobsearch import store
from app.services.jobsearch.sources.base import JobPosting
from app.services.structured_resume import StructuredResume
from app.services.structured_resume import save as save_resume

client = TestClient(app)


def setup_function():
    (DATA_DIR / "app.db").unlink(missing_ok=True)
    db._migrated_paths.clear()


def _confirm_resume():
    save_resume(
        StructuredResume.model_validate(
            {"contact": {"name": "Alex"}, "experience": [{"title": "Intern"}]}
        ),
        "h",
        True,
    )


def test_meta_and_profile_flow():
    meta = client.get("/jobs/meta").json()
    assert any(c["code"] == "de" and c["adzuna"] for c in meta["countries"])
    assert (
        client.post("/jobs/profile/suggest", json={}).status_code == 400
    )  # resume not confirmed
    _confirm_resume()
    raw = json.dumps(
        {
            "titles": ["Data Scientist"],
            "seniority": "entry",
            "countries": ["de"],
            "questions": [
                {"id": "visa", "question": "Need a visa?", "options": ["yes", "no"]}
            ],
        }
    )
    with patch("app.services.generation.llm.generate_with_fallback", return_value=raw):
        suggested = client.post(
            "/jobs/profile/suggest", json={"ambitions": "Germany startups"}
        ).json()
    assert suggested["questions"][0]["id"] == "visa"
    assert client.get("/jobs/profile").json()["confirmed"] is False
    prof = suggested["profile"] | {
        "needs_sponsorship": True,
        "clarifications": [{"question": "Need a visa?", "answer": "yes"}],
    }
    saved = client.put("/jobs/profile", json=prof)
    assert saved.status_code == 200 and saved.json()["confirmed"] is True
    assert client.put("/jobs/profile", json=prof | {"titles": []}).status_code == 400


def test_list_filters_status_and_people_at_company():
    _confirm_resume()
    [a] = store.upsert_postings(
        [
            JobPosting(
                "apify",
                "1",
                "ML Engineer",
                "TinyAI",
                "Berlin",
                "de",
                "x",
                False,
                "u1",
                company_size=20,
            )
        ]
    )
    [b] = store.upsert_postings(
        [
            JobPosting(
                "adzuna", "2", "Data Analyst", "BigCorp", "Pune", "in", "y", True, "u2"
            )
        ]
    )
    store.save_review(b, {"german_required": "yes", "german_level": "C1"}, 50, {})
    jobs = client.get("/jobs").json()["jobs"]
    by_id = {j["id"]: j for j in jobs}
    assert by_id[a]["company_kind"] == "startup" and by_id[a]["company_kind_verified"]
    assert by_id[b]["via_adzuna"] and by_id[b]["german_gap"]
    assert [j["id"] for j in client.get("/jobs?startup_only=true").json()["jobs"]] == [
        a
    ]
    assert b not in [
        j["id"] for j in client.get("/jobs?hide_german_required=true").json()["jobs"]
    ]
    assert (
        client.post(f"/jobs/{a}/status", json={"status": "saved"}).json()["status"]
        == "saved"
    )
    assert client.post(f"/jobs/{a}/status", json={"status": "nope"}).status_code == 400
    assert (
        client.post("/jobs/missing/status", json={"status": "saved"}).status_code == 404
    )

    url = "https://www.linkedin.com/in/riya"
    GENERATED_MESSAGES.write_text(
        json.dumps(
            {
                url: {
                    "generations": [
                        {
                            "generated_message": "hi",
                            "generated_at": "2026-11-01 10:00:00",
                        }
                    ]
                }
            }
        )
    )
    ENRICH_DATA.write_text(
        json.dumps(
            {
                url: {
                    "card_info": {"name": "Riya", "current_company_name": "TinyAI GmbH"}
                }
            }
        )
    )
    people = client.get(f"/jobs/{a}/people").json()
    assert people and people[0]["name"] == "Riya"


def test_search_requires_setup():
    r = client.post("/jobs/search", json={})
    assert r.status_code == 400 and "resume" in r.json()["detail"]
