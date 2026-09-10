import json
from unittest.mock import patch

from app.services.user_communication import (
    get_user_communication,
    get_user_communication_prompt,
)


def test_get_user_communication_from_file(tmp_path):
    """Test get_user_communication retrieves saved style from JSON."""
    style_file = tmp_path / "style.json"
    style_file.write_text(
        json.dumps({"content": "Direct and concise style."}), encoding="utf-8"
    )

    config = {"output_path": str(style_file), "default": "Default style"}
    style = get_user_communication(config)
    assert style == "Direct and concise style."


def test_get_user_communication_fallback(tmp_path):
    """Test get_user_communication falls back to default if file is missing."""
    config = {
        "output_path": str(tmp_path / "non_existent.json"),
        "default": "Default style fallback",
    }
    style = get_user_communication(config)
    assert style == "Default style fallback"


@patch("app.services.user_communication.load_config")
def test_get_user_communication_prompt(mock_load):
    """Test get_user_communication_prompt loads prompt YAML config."""
    mock_load.return_value = {"prompt": "Tell us about your style", "default": "Casual"}
    with patch("os.path.exists", return_value=True):
        config = get_user_communication_prompt()
        assert config["prompt"] == "Tell us about your style"
