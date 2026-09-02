import pytest
from job_search_assistant.services.helper import load_config


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
