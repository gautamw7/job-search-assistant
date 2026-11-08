"""Phase 4: the old JSON stores are imported into SQLite once, kept as backups."""

import json

from app.core.settings import DATA_DIR, ENRICH_DATA, GENERATED_MESSAGES
from app.services import usage
from app.services.enrich.store import cached_enrich_data, get_profile, load_all_profiles
from app.services.generation import load_generated_messages
from app.services.generation.store import append_generation, get_entry
from app.services.legacy_import import absorb_legacy_json
from app.services.tracker import list_contacts, update_tracking

URL = "https://www.linkedin.com/in/legacy"


def setup_function():
    for p in DATA_DIR.glob("*.bak-*"):
        p.unlink()


def _write_history():
    GENERATED_MESSAGES.write_text(
        json.dumps(
            {
                URL + "/": {  # legacy non-canonical key
                    "context": {"user_resume": "old snapshot"},
                    "tracking": {"status": "replied", "notes": "call booked"},
                    "generations": [
                        {
                            "generated_message": "second",
                            "generated_at": "2026-02-01 10:00:00",
                        },
                        {
                            "generated_message": "first",
                            "generated_at": "2026-01-01 10:00:00",
                        },
                    ],
                }
            }
        )
    )


def test_history_tracking_and_extras_are_imported_in_order_and_file_backed_up():
    _write_history()
    history = load_generated_messages()  # import happens lazily on read
    entry = history[URL]
    assert [g["generated_message"] for g in entry["generations"]] == ["first", "second"]
    assert entry["tracking"]["status"] == "replied" and entry["context"] == {
        "user_resume": "old snapshot"
    }
    assert not GENERATED_MESSAGES.exists()
    assert len(list(DATA_DIR.glob("generated_messages.json.bak-imported-*"))) == 1
    assert list_contacts()[0]["notes"] == "call booked"


def test_reimport_merges_without_duplicating():
    _write_history()
    load_generated_messages()
    append_generation(
        URL, {"generated_message": "third", "generated_at": "2026-03-01 10:00:00"}
    )
    _write_history()  # an old backup restored by hand
    msgs = [g["generated_message"] for g in get_entry(URL)["generations"]]
    assert msgs == ["first", "second", "third"]


def test_tracker_updates_work_after_import():
    _write_history()
    t = update_tracking(URL, status="interviewing", notes="round 2")
    assert t["status"] == "interviewing"
    assert get_entry(URL)["tracking"]["notes"] == "round 2"


def test_profiles_keep_the_newest_copy():
    ENRICH_DATA.write_text(
        json.dumps(
            {
                URL: {
                    "card_info": {"name": "Old"},
                    "content": {"a": 1},
                    "fetched_at": "2026-01-01T00:00:00",
                },
                "https://www.linkedin.com/in/legacy-string": "pre-2026 string entry",
            }
        )
    )
    absorb_legacy_json()
    assert get_profile(URL)["card_info"]["name"] == "Old"
    assert (
        cached_enrich_data(URL) == {}
    )  # fetched long ago: past the 30-day cache window
    ENRICH_DATA.write_text(
        json.dumps(
            {
                URL: {
                    "card_info": {"name": "Older"},
                    "content": {"a": 1},
                    "fetched_at": "2025-01-01T00:00:00",
                },
            }
        )
    )
    absorb_legacy_json()
    assert load_all_profiles()[URL]["card_info"]["name"] == "Old"  # older copy ignored
    assert "https://www.linkedin.com/in/legacy-string" not in load_all_profiles()


def test_usage_ledger_imported():
    (DATA_DIR / "usage.json").write_text(
        json.dumps(
            {
                "events": [
                    {"kind": "brightdata", "profiles": 4, "ts": "2026-11-02T10:00:00"},
                    {
                        "kind": "gemini",
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "ts": "2026-11-02T10:00:01",
                    },
                    {"bad": "row"},
                ]
            }
        )
    )
    month = usage._totals_since("2026-11")
    assert month["brightdata_profiles"] == 4 and month["gemini_calls"] == 1
    assert not (DATA_DIR / "usage.json").exists()


def test_corrupt_legacy_file_is_quarantined_not_lost():
    GENERATED_MESSAGES.write_text('{"truncated": ')
    assert load_generated_messages() == {}
    assert list(DATA_DIR.glob("generated_messages.json.corrupt-*"))
    for p in DATA_DIR.glob("generated_messages.json.corrupt-*"):
        p.unlink()
