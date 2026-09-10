from unittest.mock import patch

from app.services.resources import build_resources


@patch("app.services.resources.check_resume_markdown")
@patch("app.services.resources.get_resume_markdown")
@patch("app.services.resources.load_config")
@patch("app.services.resources.get_user_communication")
def test_build_resources(mock_get_comm, mock_load_config, mock_get_md, mock_check_md):
    """Test build_resources assembles all required resources correctly."""
    mock_check_md.return_value = True
    mock_get_md.return_value = "Markdown resume content"

    def config_side_effect(path):
        if "user_communication" in path:
            return {"default": "Default style"}
        elif "outreach_message" in path:
            return {
                "system_prompt": "Sys prompt",
                "user_prompt_template": "Template {recipient_enrich_data}",
            }
        elif "user_preferences" in path:
            return {"default": {"tone": "friendly"}}
        return {}

    mock_load_config.side_effect = config_side_effect
    mock_get_comm.return_value = "User comm style"

    with patch("os.path.exists", return_value=True):
        resources = build_resources()
        assert resources["user_resume"] == "Markdown resume content"
        assert resources["user_communication_style"] == "User comm style"
        assert resources["system_prompt"] == "Sys prompt"
        assert resources["template"] == "Template {recipient_enrich_data}"
        assert resources["user_preferences"] == {"tone": "friendly"}
