import pytest

from app.services.enrich.processor import (
    HIRING_REGEX,
    activity_to_markdown,
    content_to_markdown,
    is_error_record,
)
from app.services.enrich.store import _pick_record, save_enrich_data


def test_hiring_regex_is_not_fooled_by_generic_phrases():
    assert HIRING_REGEX.search("We're hiring backend engineers")
    assert HIRING_REGEX.search("Our team is looking for a designer")
    assert not HIRING_REGEX.search("Looking for inspiration on a Monday")


def test_markdown_has_no_python_reprs_and_is_bounded():
    md = content_to_markdown(
        {"experience": [{"title": "Eng", "positions": [{"role": "Dev"}]}] * 40}
    )
    assert "{'" not in md and "[{" not in md
    assert "more omitted" in md


def test_activity_markdown_lists_hiring_posts_only():
    activity = {"hiring": [{"title": "We are hiring SREs", "link": "http://x"}]}
    assert "We are hiring SREs" in activity_to_markdown(activity)
    assert activity_to_markdown({"hiring": []}) == ""


def test_error_rows_are_never_used_as_profiles():
    err = {"input_url": "https://www.linkedin.com/in/x", "error": "blocked"}
    assert is_error_record(err)
    with pytest.raises(ValueError, match="could not be scraped"):
        _pick_record([err], "https://www.linkedin.com/in/x")


def test_record_matched_by_url_not_position():
    rows = [
        {"input_url": "https://www.linkedin.com/in/other", "name": "Other"},
        {"input_url": "https://www.linkedin.com/in/me/", "name": "Me"},
    ]
    assert _pick_record(rows, "https://www.linkedin.com/in/me")["name"] == "Me"


def test_refresh_replaces_instead_of_accumulating(tmp_path):
    out = str(tmp_path / "enrich.json")
    url = "https://www.linkedin.com/in/me"
    save_enrich_data({url: {"content": {"experience": [{"t": "old"}]}}}, out)
    save_enrich_data({url: {"content": {"experience": [{"t": "new"}]}}}, out)
    import json
    from pathlib import Path

    saved = json.loads(Path(out).read_text(encoding="utf-8"))
    assert saved[url]["content"]["experience"] == [{"t": "new"}]
