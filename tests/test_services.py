import pytest
import os
from unittest.mock import patch, MagicMock
from services.helper import load_config
from services.enrich import process_enrich_data, map_enrich_data_by_url, get_enrich_data
from services.generator import generate_outreach_message


def test_load_config_valid(tmp_path):
    """Test loading configuration from a valid YAML file."""
    d = tmp_path / "config"
    d.mkdir()
    p = d / "test.yaml"
    p.write_text("key: value", encoding="utf-8")

    cfg = load_config(str(p))
    assert cfg == {"key": "value"}


def test_load_config_not_found():
    """Test that load_config raises FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        load_config("non_existent_config_file_12345.yaml")


def test_process_enrich_data():
    """Test processing raw dictionary structure into indented tree string."""
    sample_data = {
        "name": "Jane Doe",
        "experience": [
            {"title": "Engineer", "company": "TechCorp"}
        ]
    }
    res = process_enrich_data(sample_data)
    assert "Jane Doe" in res
    assert "TechCorp" in res


def test_map_enrich_data_by_url():
    """Test mapping list of enrichment responses keyed by input URL."""
    results = [
        {"input_url": "https://www.linkedin.com/in/test1", "name": "Test 1"},
        {"name": "No URL test"},
        {"input_url": "https://www.linkedin.com/in/test2", "name": "Test 2"}
    ]
    mapped = map_enrich_data_by_url(results)
    assert "https://www.linkedin.com/in/test1" in mapped
    assert "https://www.linkedin.com/in/test2" in mapped
    assert len(mapped) == 2


@patch("services.enrich.fetch_enrich_data")
@patch("services.enrich.save_enrich_data")
def test_get_enrich_data(mock_save, mock_fetch):
    """Test get_enrich_data fetches and formats single LinkedIn profile enrichment."""
    mock_fetch.return_value = [
        {"input_url": "https://www.linkedin.com/in/test", "name": "Test User"}
    ]
    res = get_enrich_data("https://www.linkedin.com/in/test")
    assert "Test User" in res
    mock_fetch.assert_called_once_with(["https://www.linkedin.com/in/test"])
    mock_save.assert_called_once()


@patch("services.generator.get_enrich_data")
@patch("services.generator.genai.Client")
@patch("services.generator.build_resources")
@patch("services.generator.load_generated_messages")
@patch("services.generator.save_generated_messages")
def test_generate_outreach_message(mock_save_msg, mock_load_msg, mock_build_res, mock_client, mock_enrich):
    """Test generating outreach message for a single target profile."""
    mock_enrich.return_value = "Enrichment text representation."
    mock_load_msg.return_value = {}
    mock_build_res.return_value = {
        "user_resume": "Resume",
        "user_communication_style": "Style",
        "system_prompt": "System instructions",
        "template": "Hello {recipient_enrich_data}. Note: {user_notes}",
        "user_preferences": {"tone": "polite"},
        "user_note": "Friendly hello"
    }

    # Mock Gemini Client and API response
    mock_gen_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Generated message content."
    mock_gen_client.models.generate_content.return_value = mock_response
    mock_client.return_value = mock_gen_client

    result = generate_outreach_message(
        linkedin_url="https://www.linkedin.com/in/test",
        user_note="Custom note",
        user_preferences={"tone": "assertive"}
    )

    assert result == "Generated message content."
    mock_enrich.assert_called_once_with("https://www.linkedin.com/in/test")
    mock_save_msg.assert_called_once()
