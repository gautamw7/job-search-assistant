from unittest.mock import patch

from fastapi.testclient import TestClient
from job_search_assistant.api.main import app

client = TestClient(app)


def test_get_targets_keys():
    """Test retrieving list of target keys from history."""
    response = client.get("/messages/targets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@patch("job_search_assistant.api.routers.messages.generate_outreach_message")
def test_create_message_success(mock_generate):
    """Test generating a single outreach message successfully."""
    mock_generate.return_value = "Mocked outreach message response."
    payload = {
        "linkedin_url": "https://www.linkedin.com/in/gautamw",
        "additional_note": "Interested in AI",
        "additional_preferences": {
            "length": "short",
            "tone": "professional",
            "formality": "balanced",
            "directness": "direct",
            "style": "polished",
        },
    }
    response = client.post("/messages/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["linkedin_url"] == payload["linkedin_url"]
    assert data["generated_message"] == "Mocked outreach message response."
    assert data["status"] == "success"
    assert data["error"] is None


@patch("job_search_assistant.api.routers.messages.generate_outreach_message")
def test_create_message_failure_bubbles_up(mock_generate):
    """Test that model failure during single generation bubbles up as an HTTP error."""
    mock_generate.side_effect = RuntimeError("Gemini service unavailable")
    payload = {
        "linkedin_url": "https://www.linkedin.com/in/gautamw",
        "additional_note": "Interested in AI",
        "additional_preferences": None,
    }
    response = client.post("/messages/", json=payload)
    assert response.status_code == 500
    assert "Gemini service unavailable" in response.json()["detail"]


@patch("job_search_assistant.api.routers.messages.generate_outreach_message")
def test_create_message_invalid_url(mock_generate):
    """Test that single generation validates LinkedIn URL format."""
    payload = {
        "linkedin_url": "https://github.com/gautamw",
        "additional_note": None,
        "additional_preferences": None,
    }
    response = client.post("/messages/", json=payload)
    assert response.status_code == 422


@patch("job_search_assistant.api.routers.messages.generate_outreach_message")
def test_create_messages_batch_success(mock_generate):
    """Test batch outreach message generation with multithreading."""
    mock_generate.return_value = "Mocked batch response."
    payload = [
        {
            "linkedin_url": "https://www.linkedin.com/in/test1",
            "additional_note": "A note",
            "additional_preferences": None,
        },
        {
            "linkedin_url": "https://www.linkedin.com/in/test2",
            "additional_note": "Another note",
            "additional_preferences": None,
        },
    ]
    response = client.post("/messages/batch", json=payload)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    for item in results:
        assert item["status"] == "success"
        assert item["generated_message"] == "Mocked batch response."
        assert item["error"] is None


@patch("job_search_assistant.api.routers.messages.generate_outreach_message")
def test_create_messages_batch_all_failure_bubbles_up(mock_generate):
    """Test that total batch generation failure bubbles up as an HTTP 500 error."""
    mock_generate.side_effect = RuntimeError("Gemini quota exceeded")
    payload = [
        {
            "linkedin_url": "https://www.linkedin.com/in/test1",
            "additional_note": None,
            "additional_preferences": None,
        }
    ]
    response = client.post("/messages/batch", json=payload)
    assert response.status_code == 500
    assert "Gemini quota exceeded" in response.json()["detail"]


@patch("job_search_assistant.api.routers.messages.regenerate_responses")
def test_regenerate_message(mock_regenerate):
    """Test regenerating outreach message."""
    mock_regenerate.return_value = {
        "linkedin_url": "https://www.linkedin.com/in/gautamw",
        "generated_message": "Mocked regenerated message.",
        "generated_at": "2026-08-30 15:00:00",
    }
    payload = {
        "linkedin_url": "https://www.linkedin.com/in/gautamw",
        "additional_note": "Make it shorter",
        "additional_preferences": {
            "length": "short",
            "tone": "professional",
            "formality": "balanced",
            "directness": "direct",
            "style": "concise",
        },
    }
    response = client.post("/messages/regenerate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["generated_message"] == "Mocked regenerated message."
    assert data["status"] == "success"


@patch("job_search_assistant.api.routers.messages.regenerate_responses")
def test_regenerate_message_failure_bubbles_up(mock_regenerate):
    """Test that model failure during regeneration bubbles up as an HTTP error."""
    mock_regenerate.side_effect = RuntimeError("Gemini model overloaded")
    payload = {
        "linkedin_url": "https://www.linkedin.com/in/gautamw",
        "additional_note": "Make it shorter",
        "additional_preferences": None,
    }
    response = client.post("/messages/regenerate", json=payload)
    assert response.status_code == 500
    assert "Gemini model overloaded" in response.json()["detail"]


def test_get_messages_not_found():
    """Test GET /messages/?linkedin_url=... returns 404 for unknown profile URL."""
    with patch("json.load", return_value={}), patch("builtins.open"):
        response = client.get(
            "/messages/?linkedin_url=https://www.linkedin.com/in/unknown_user"
        )
        assert response.status_code == 404


def test_get_messages_found():
    """Test GET /messages/?linkedin_url=... returns latest generated message."""
    mock_history = {
        "https://www.linkedin.com/in/testuser": {
            "generations": [
                {
                    "generated_message": "Hello from history!",
                    "generated_at": "2026-08-30 12:00:00",
                }
            ]
        }
    }
    with patch("json.load", return_value=mock_history), patch("builtins.open"):
        response = client.get(
            "/messages/?linkedin_url=https://www.linkedin.com/in/testuser"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["generated_message"] == "Hello from history!"
        assert data["linkedin_url"] == "https://www.linkedin.com/in/testuser"
