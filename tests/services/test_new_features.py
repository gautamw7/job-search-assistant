"""Hiring contacts, shared background, fact check, tracker, follow-ups, usage/budget."""

import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.core.settings import DATA_DIR, ENRICH_DATA, GENERATED_MESSAGES
from app.services import tracker, usage
from app.services.background import shared_background
from app.services.enrich import enrich_many, hiring_contacts
from app.services.enrich.processor import contact_hiring_signals
from app.services.factcheck import _parse_issues, fact_check

ME = "https://www.linkedin.com/in/me"
RECRUITER = "https://www.linkedin.com/in/riya-recruits"
ENGINEER = "https://www.linkedin.com/in/sam-eng"


@pytest.fixture(autouse=True)
def clean_data():
    for name in (
        "enrich_data.json",
        "generated_messages.json",
        "usage.json",
        "settings.json",
    ):
        (DATA_DIR / name).unlink(missing_ok=True)
    usage._scope_totals.clear()
    yield


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


# ---- hiring contacts -------------------------------------------------------------


def test_contact_signals_catch_recruiters_not_random_words():
    assert contact_hiring_signals("Senior Talent Acquisition Partner | We're hiring!")
    assert contact_hiring_signals("Technical Recruiter at Acme")
    assert contact_hiring_signals("Backend engineer, coffee lover") == []


def test_hiring_contacts_lists_people_also_viewed_with_signals():
    _write(
        ENRICH_DATA,
        {
            ME: {
                "card_info": {"name": "Me"},
                "discovery": {
                    "people_also_viewed": [
                        {
                            "name": "Sam",
                            "about": "Backend engineer",
                            "profile_link": "https://in.linkedin.com/in/sam-eng",
                        },
                        {
                            "name": "Riya",
                            "about": "Technical Recruiter",
                            "profile_link": RECRUITER + "/",
                        },
                        {
                            "name": "Co",
                            "about": "x",
                            "profile_link": "https://www.linkedin.com/company/acme",
                        },
                    ]
                },
            },
            ENGINEER: {
                "card_info": {"name": "Sam"},
                "activity": {"hiring": [{"title": "We're hiring SREs"}], "dropped": []},
            },
        },
    )
    contacts = hiring_contacts(ME)
    urls = [c["linkedin_url"] for c in contacts]
    assert urls == [
        ENGINEER,
        RECRUITER,
    ]  # company pages skipped; known hiring posts first
    assert contacts[0]["checked"] and contacts[0]["hiring_posts"] == 1
    assert contacts[1]["signals"] == ["Recruiter"] and not contacts[1]["checked"]


def test_enrich_many_uses_one_brightdata_request_and_skips_cache():
    _write(
        ENRICH_DATA,
        {ENGINEER: {"card_info": {"name": "Sam"}, "content": {"about": "x"}}},
    )
    rows = [
        {
            "input_url": RECRUITER,
            "name": "Riya",
            "activity": [{"title": "We are hiring data scientists"}],
        },
    ]
    with patch("app.services.enrich.fetch_enrich_data", return_value=rows) as fetch:
        out = enrich_many([ENGINEER, RECRUITER, "https://www.linkedin.com/in/ghost"])
    fetch.assert_called_once_with([RECRUITER, "https://www.linkedin.com/in/ghost"])
    assert out[ENGINEER]["cached"] is True
    assert out[RECRUITER]["hiring_posts"] == 1
    assert out["https://www.linkedin.com/in/ghost"]["ok"] is False


# ---- shared background ---------------------------------------------------------


def test_shared_background_only_reports_real_overlaps():
    resume = "B.Tech, Vellore Institute of Technology. Intern at Syngenta, Pune, India."
    profile = {
        "card_info": {
            "current_company_name": "Syngenta",
            "location": "Pune, Maharashtra",
        },
        "content": {
            "education": [
                {"title": "Vellore Institute of Technology"},
                {"title": "MIT"},
            ]
        },
    }
    hooks = shared_background(resume, profile)
    assert any("Vellore Institute of Technology" in h for h in hooks)
    assert any("Syngenta" in h for h in hooks)
    assert any("Pune" in h for h in hooks)
    assert not any("MIT" in h for h in hooks)
    assert shared_background(resume, {"card_info": {"location": "Berlin"}}) == []


# ---- fact check ----------------------------------------------------------------


def test_fact_check_parses_json_and_flags():
    raw = '```json\n{"issues": [{"claim": "I led a team of 10", "reason": "not in resume"}]}\n```'
    assert _parse_issues(raw) == [
        {"claim": "I led a team of 10", "reason": "not in resume"}
    ]
    with patch(
        "app.services.generation.llm.generate_with_fallback",
        return_value='{"issues": []}',
    ):
        assert fact_check("Hi", user_resume="r", recipient="p")["status"] == "pass"
    with patch("app.services.generation.llm.generate_with_fallback", return_value=raw):
        result = fact_check("Hi", user_resume="r", recipient="p")
    assert result["status"] == "flagged" and len(result["issues"]) == 1


def test_fact_check_never_blocks_and_can_be_disabled():
    with patch(
        "app.services.generation.llm.generate_with_fallback",
        side_effect=RuntimeError("quota"),
    ):
        assert fact_check("Hi", user_resume="r", recipient="p")["status"] == "error"
    usage.save_settings({"fact_check_enabled": False})
    assert fact_check("Hi", user_resume="r", recipient="p")["status"] == "skipped"


# ---- tracker + follow-ups --------------------------------------------------------


def _history(**tracking):
    entry = {
        "generations": [
            {"generated_message": "Hey", "generated_at": "2026-11-01 10:00:00"}
        ]
    }
    if tracking:
        entry["tracking"] = tracking
    _write(GENERATED_MESSAGES, {ME: entry})


def test_marking_sent_sets_timestamps_and_followup_schedule():
    _history()
    t = tracker.update_tracking(ME, status="sent")
    assert t["sent_at"] and t["last_contact_at"]
    contact = tracker.list_contacts()[0]
    assert contact["status"] == "sent" and contact["followup_due"] is False
    with pytest.raises(ValueError):
        tracker.update_tracking(ME, status="ghosted")
    with pytest.raises(tracker.ContactNotFoundError):
        tracker.update_tracking("https://www.linkedin.com/in/nobody", status="sent")


def test_followup_due_after_wait_and_stops_after_max():
    old = (datetime.now() - timedelta(days=tracker.FOLLOWUP_AFTER_DAYS + 1)).isoformat()
    _history(status="sent", sent_at=old, last_contact_at=old, followup_count=0)
    assert tracker.list_contacts()[0]["followup_due"] is True
    tracker.update_tracking(ME, followup_sent=True)
    assert tracker.list_contacts()[0]["followup_due"] is False  # clock restarted
    _history(
        status="sent",
        sent_at=old,
        last_contact_at=old,
        followup_count=tracker.MAX_FOLLOWUPS,
    )
    assert tracker.list_contacts()[0]["followup_due"] is False
    _history(status="replied", sent_at=old, last_contact_at=old)
    assert tracker.list_contacts()[0]["followup_due"] is False


def test_generate_followup_saves_a_followup_record():
    _history(status="sent", sent_at="2026-11-01T10:00:00")
    resources = {
        "user_resume": "Resume",
        "user_communication_style": "Style",
        "system_prompt": "Sys",
        "template": "",
        "user_preferences": "",
        "user_note": "",
    }
    with (
        patch(
            "app.services.generation.service.build_resources", return_value=resources
        ),
        patch(
            "app.services.generation.service.get_enrich_data", return_value="Profile"
        ),
        patch(
            "app.services.generation.service.generate_with_fallback",
            return_value="Quick follow-up",
        ),
        patch(
            "app.services.generation.service.fact_check",
            return_value={"status": "pass", "issues": []},
        ),
    ):
        from app.services.generation import generate_followup

        record = generate_followup(ME)
    assert (
        record["kind"] == "followup"
        and record["generated_message"] == "Quick follow-up"
    )
    from app.services.generation import load_generated_messages

    saved = load_generated_messages()[ME]["generations"]
    assert [g.get("kind", "outreach") for g in saved] == ["outreach", "followup"]
    assert tracker.list_contacts()[0]["original_message"] == "Hey"


# ---- usage + budget --------------------------------------------------------------


def test_usage_is_recorded_scoped_and_costed():
    usage.save_settings(
        {
            "pricing": {
                "brightdata_per_profile": 0.01,
                "gemini_input_per_million": 1,
                "gemini_output_per_million": 2,
            }
        }
    )
    with usage.usage_scope("job1"):
        usage.record_brightdata(3)
        usage.record_gemini("m", 1_000_000, 500_000, "outreach")
    run = usage.scope_totals("job1")
    assert run["brightdata_profiles"] == 3 and run["gemini_calls"] == 1
    assert run["estimated_cost"] == pytest.approx(0.03 + 1 + 1)
    assert usage.summary()["month"]["brightdata_profiles"] == 3


def test_free_tier_assumed_until_prices_set_and_budget_blocks_spending():
    usage.record_brightdata(5)
    month = usage.summary()["month"]
    assert month["estimated_cost"] == 0.0 and month["free_tier_assumed"] is True
    usage.save_settings({"budget": {"monthly_profiles": 6}})
    usage.check_budget(profiles=1)  # exactly at the limit is fine
    with pytest.raises(usage.BudgetExceededError):
        usage.check_budget(profiles=2)
    with pytest.raises(ValueError):
        usage.save_settings({"budget": {"monthly_usd": -1}})
