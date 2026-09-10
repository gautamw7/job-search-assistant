from unittest.mock import MagicMock, patch

from app.services.generation.service import generate_outreach_message


@patch("app.services.generation.service.get_enrich_data")
@patch("app.services.generation.llm.genai.Client")
@patch("app.services.generation.service.build_resources")
@patch("app.services.generation.service.load_generated_messages")
@patch("app.services.generation.service.save_generated_messages")
def test_generate_outreach_message(
    mock_save_msg, mock_load_msg, mock_build_res, mock_client, mock_enrich
):
    mock_enrich.return_value = "Enrichment text representation."
    mock_load_msg.return_value = {}
    mock_build_res.return_value = {
        "user_resume": "Resume",
        "user_communication_style": "Style",
        "system_prompt": "System instructions",
        "template": "Hello {recipient_enrich_data}. Note: {user_notes}",
        "user_preferences": {"tone": "polite"},
        "user_note": "Friendly hello",
    }

    mock_gen_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Generated message content."
    mock_gen_client.models.generate_content.return_value = mock_response
    mock_client.return_value = mock_gen_client

    result = generate_outreach_message(
        linkedin_url="https://www.linkedin.com/in/test",
        user_note="Custom note",
        user_preferences={"tone": "assertive"},
    )

    assert result == "Generated message content."
    mock_enrich.assert_called_once_with("https://www.linkedin.com/in/test")
    mock_save_msg.assert_called_once()
