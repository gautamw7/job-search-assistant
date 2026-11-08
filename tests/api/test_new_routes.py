import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.app import app
from app.core.settings import DATA_DIR, GENERATED_MESSAGES

client = TestClient(app)
URL = "https://www.linkedin.com/in/route-test"


def setup_function():
    GENERATED_MESSAGES.write_text(
        json.dumps(
            {
                URL: {
                    "generations": [
                        {
                            "generated_message": "Hi",
                            "generated_at": "2026-11-01 10:00:00",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    (DATA_DIR / "settings.json").unlink(missing_ok=True)


def test_tracker_list_and_update():
    data = client.get("/tracker/").json()
    assert data["statuses"][0] == "drafted"
    assert any(c["linkedin_url"] == URL for c in data["contacts"])
    r = client.post(
        "/tracker/update",
        json={"linkedin_url": URL, "status": "sent", "notes": "sent via InMail"},
    )
    assert r.status_code == 200 and r.json()["status"] == "sent"
    assert (
        client.post(
            "/tracker/update", json={"linkedin_url": URL, "status": "nope"}
        ).status_code
        == 422
    )
    missing = client.post(
        "/tracker/update", json={"linkedin_url": URL + "x", "status": "sent"}
    )
    assert missing.status_code == 404


def test_followup_route():
    with patch(
        "app.api.routers.messages.generate_followup",
        return_value={
            "generated_message": "Nudge",
            "generated_at": "2026-11-08 10:00:00",
            "fact_check": {"status": "pass", "issues": []},
            "shared_background": [],
        },
    ):
        r = client.post("/messages/followup", json={"linkedin_url": URL})
    assert r.status_code == 200
    assert (
        r.json()["generated_message"] == "Nudge"
        and r.json()["fact_check"]["status"] == "pass"
    )


def test_usage_settings_roundtrip_and_validation():
    r = client.put(
        "/usage/settings",
        json={"budget": {"monthly_profiles": 100}, "fact_check_enabled": False},
    )
    assert r.status_code == 200
    body = client.get("/usage/").json()
    assert body["settings"]["budget"]["monthly_profiles"] == 100
    assert body["settings"]["fact_check_enabled"] is False
    assert body["pricing_configured"] is False
    assert (
        client.put("/usage/settings", json={"budget": {"bogus": 1}}).status_code == 400
    )


def test_hiring_contacts_404_for_unknown_profile_and_batch_validation():
    assert client.get(f"/enrich/{URL}/hiring-contacts").status_code in (404, 500)
    assert (
        client.post(
            "/enrich/batch", json={"linkedin_urls": ["https://github.com/x"]}
        ).status_code
        == 422
    )
