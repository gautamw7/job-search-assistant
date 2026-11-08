import json
from unittest.mock import patch

from app.services.enrich import (
    generate_input_json,
    get_enrich_data,
    map_enrich_data_by_url,
    process_enrich_data,
    save_enrich_data,
)


def test_generate_input_json():
    """Test payload generation for BrightData API."""
    urls = ["https://www.linkedin.com/in/john", "https://www.linkedin.com/in/jane"]
    payload = generate_input_json(urls)
    assert payload == [
        {"url": "https://www.linkedin.com/in/john"},
        {"url": "https://www.linkedin.com/in/jane"},
    ]


def test_save_enrich_data_merge(tmp_path):
    """Test saving enrichment data and merging with existing history."""
    output_file = tmp_path / "enrich_data.json"
    data1 = {"url1": "content1"}
    save_enrich_data(data1, output_path=str(output_file))

    data2 = {"url2": "content2"}
    save_enrich_data(data2, output_path=str(output_file))

    with open(output_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == {"url1": "content1", "url2": "content2"}


def test_process_enrich_data():
    """Test processing raw dictionary into dict buckets (card, content, activity, discovery)."""
    sample_data = {
        "name": "Jane Doe",
        "id": "jane-doe",
        "url": "https://www.linkedin.com/in/jane-doe",
        "followers": 100,
        "connections": 500,
        "current_company_name": "TechCorp",
        "location": "Bengaluru",
        "about": "Engineer at TechCorp",
        "experience": [{"title": "Engineer", "company": "TechCorp"}],
        "activity": [
            {"title": "We are hiring Engineers", "link": "https://example.com/1"},
            {"title": "Just a normal post", "link": "https://example.com/2"},
        ],
        "people_also_viewed": [
            {"name": "John Doe", "profile_link": "https://linkedin.com/in/john"}
        ],
    }
    res = process_enrich_data(sample_data)
    # card_info should contain name etc
    assert res["card_info"]["name"] == "Jane Doe"
    assert res["card_info"]["current_company_name"] == "TechCorp"
    # content should contain about and experience
    assert res["content"]["about"] == "Engineer at TechCorp"
    assert res["activity"]["hiring"][0]["title"] == "We are hiring Engineers"
    assert len(res["activity"]["dropped"]) == 1
    assert len(res["discovery"]["people_also_viewed"]) == 1
    assert "TechCorp" in str(res["content"]["experience"])


def test_map_enrich_data_by_url():
    """Test mapping list of enrichment responses keyed by input URL."""
    results = [
        {
            "input_url": "https://www.linkedin.com/in/test1",
            "name": "Test 1",
            "about": "About Test 1",
        },
        {"name": "No URL test"},
        {
            "input_url": "https://www.linkedin.com/in/test2",
            "name": "Test 2",
            "about": "About Test 2",
        },
    ]
    mapped = map_enrich_data_by_url(results)
    assert "https://www.linkedin.com/in/test1" in mapped
    assert "https://www.linkedin.com/in/test2" in mapped
    assert len(mapped) == 2
    # each value should be processed dict
    assert mapped["https://www.linkedin.com/in/test1"]["card_info"]["name"] == "Test 1"


@patch("app.services.enrich.fetch_enrich_data")
@patch("app.services.enrich.save_enrich_data")
def test_get_enrich_data(mock_save, mock_fetch):
    """Test get_enrich_data fetches, processes [0], returns content markdown and saves full dict."""
    mock_fetch.return_value = [
        {
            "input_url": "https://www.linkedin.com/in/test",
            "name": "Test User",
            "about": "About Test User",
            "activity": [{"title": "We are hiring"}],
            "people_also_viewed": [],
        }
    ]
    res = get_enrich_data("https://www.linkedin.com/in/test")
    # should return markdown string of content (contains about)
    assert "About Test User" in res
    assert "## about" in res
    mock_fetch.assert_called_once_with(["https://www.linkedin.com/in/test"])
    mock_save.assert_called_once()
    # saved dict should contain card_info with name
    saved_arg = mock_save.call_args[0][0]
    assert "https://www.linkedin.com/in/test" in saved_arg
    assert (
        saved_arg["https://www.linkedin.com/in/test"]["card_info"]["name"]
        == "Test User"
    )


def test_save_enrich_data_default_path_uses_sqlite():
    """With no explicit path, profiles go to the database, not a JSON file."""
    from app.core.settings import ENRICH_DATA
    from app.services.enrich.store import load_all_profiles

    save_enrich_data({"url1": {"card_info": {"name": "One"}}})
    save_enrich_data({"url2": {"card_info": {"name": "Two"}}})
    save_enrich_data({"url1": {"card_info": {"name": "One v2"}}})  # replace

    assert load_all_profiles() == {
        "url1": {"card_info": {"name": "One v2"}},
        "url2": {"card_info": {"name": "Two"}},
    }
    assert not ENRICH_DATA.exists()
