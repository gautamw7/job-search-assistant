import json

from app.core.settings import DATA_DIR, ENRICH_DATA, GENERATED_MESSAGES
from app.services.migrations import normalize_keys


def test_legacy_keys_are_normalized_merged_and_backed_up():
    GENERATED_MESSAGES.write_text(
        json.dumps(
            {
                "https://www.linkedin.com/in/me/": {
                    "generations": [
                        {
                            "generated_message": "old",
                            "generated_at": "2026-01-01 10:00:00",
                        }
                    ],
                    "tracking": {"status": "replied", "updated_at": "2026-01-03"},
                },
                "https://www.linkedin.com/in/me": {
                    "generations": [
                        {
                            "generated_message": "new",
                            "generated_at": "2026-02-01 10:00:00",
                        }
                    ],
                    "tracking": {"status": "sent", "updated_at": "2026-02-02"},
                },
                "http://in.linkedin.com/in/other": {"generations": []},
            }
        )
    )
    ENRICH_DATA.write_text(
        json.dumps(
            {
                "https://www.linkedin.com/in/me/": {"content": {"a": 1}},
                "https://www.linkedin.com/in/me": {
                    "content": {"a": 1, "b": 2},
                    "fetched_at": "2026-02-01T00:00:00",
                },
            }
        )
    )

    assert normalize_keys() == {"generated_messages": 2, "enrich_data": 1}

    history = json.loads(GENERATED_MESSAGES.read_text())
    assert set(history) == {
        "https://www.linkedin.com/in/me",
        "https://www.linkedin.com/in/other",
    }
    me = history["https://www.linkedin.com/in/me"]
    assert [g["generated_message"] for g in me["generations"]] == ["old", "new"]
    assert me["tracking"]["status"] == "replied"  # furthest-along status wins
    assert json.loads(ENRICH_DATA.read_text())["https://www.linkedin.com/in/me"][
        "content"
    ] == {"a": 1, "b": 2}
    assert len(list(DATA_DIR.glob("generated_messages.json.bak-*"))) == 1

    assert normalize_keys() == {"generated_messages": 0, "enrich_data": 0}  # idempotent
    for p in DATA_DIR.glob("*.bak-*"):
        p.unlink()
