import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def backup_restore_user_communication():
    """Backup user communication style before test and restore after test."""
    path = "data/user_communication_style.json"
    backup_data = None
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                backup_data = f.read()
        except Exception:
            pass

    yield

    # Restore after test
    if backup_data is not None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(backup_data)
    elif os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


def test_root_endpoint():
    """Test that the root endpoint returns 200 or 404."""
    response = client.get("/")
    assert response.status_code in [200, 404]


def test_get_personalization_config():
    """Test getting personalization config schema."""
    response = client.get("/personalization/config")
    assert response.status_code == 200
    data = response.json()
    assert "questions" in data
    assert "description" in data


def test_user_communication_prompt():
    """Test getting user communication configuration and prompt."""
    response = client.get("/user-communication/prompt")
    assert response.status_code == 200
    data = response.json()
    assert "prompt" in data
    assert "questions" in data


def test_user_communication_get():
    """Test getting currently saved user communication style."""
    response = client.get("/user-communication/")
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "source" in data


def test_update_and_get_user_communication():
    """Test updating user communication style via POST and verifying round-trip retrieval."""
    payload = {
        "content": "Friendly, warm, DS senior style.",
        "source": "questions"
    }
    # 1. Update style
    response = client.post("/user-communication/update", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == payload["content"]
    assert data["source"] == payload["source"]

    # 2. Retrieve latest saved style and verify round-trip
    get_response = client.get("/user-communication/")
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["content"] == payload["content"]
    assert get_data["source"] == payload["source"]


def test_resume_get():
    """Test getting resume markdown."""
    response = client.get("/resume/")
    assert response.status_code in [200, 404, 204]


def test_get_targets_keys():
    """Test retrieving list of target keys from history."""
    response = client.get("/messages/targets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@patch("api.routers.messages.generate_outreach_message")
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
            "style": "polished"
        }
    }
    response = client.post("/messages/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["linkedin_url"] == payload["linkedin_url"]
    assert data["generated_message"] == "Mocked outreach message response."
    assert data["status"] == "success"
    assert data["error"] is None


@patch("api.routers.messages.generate_outreach_message")
def test_create_message_failure_bubbles_up(mock_generate):
    """Test that model failure during single generation bubbles up as an HTTP error."""
    mock_generate.side_effect = RuntimeError("Gemini service unavailable")
    payload = {
        "linkedin_url": "https://www.linkedin.com/in/gautamw",
        "additional_note": "Interested in AI",
        "additional_preferences": None
    }
    response = client.post("/messages/", json=payload)
    assert response.status_code == 500
    assert "Gemini service unavailable" in response.json()["detail"]


@patch("api.routers.messages.generate_outreach_message")
def test_create_message_invalid_url(mock_generate):
    """Test that single generation validates LinkedIn URL format."""
    payload = {
        "linkedin_url": "https://github.com/gautamw",
        "additional_note": None,
        "additional_preferences": None
    }
    response = client.post("/messages/", json=payload)
    assert response.status_code == 422  # Validation Error


@patch("api.routers.messages.generate_outreach_message")
def test_create_messages_batch_success(mock_generate):
    """Test batch outreach message generation with multithreading."""
    mock_generate.return_value = "Mocked batch response."
    payload = [
        {
            "linkedin_url": "https://www.linkedin.com/in/test1",
            "additional_note": "A note",
            "additional_preferences": None
        },
        {
            "linkedin_url": "https://www.linkedin.com/in/test2",
            "additional_note": "Another note",
            "additional_preferences": None
        }
    ]
    response = client.post("/messages/batch", json=payload)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    for item in results:
        assert item["status"] == "success"
        assert item["generated_message"] == "Mocked batch response."
        assert item["error"] is None


@patch("api.routers.messages.generate_outreach_message")
def test_create_messages_batch_all_failure_bubbles_up(mock_generate):
    """Test that total batch generation failure bubbles up as an HTTP 500 error."""
    mock_generate.side_effect = RuntimeError("Gemini quota exceeded")
    payload = [
        {
            "linkedin_url": "https://www.linkedin.com/in/test1",
            "additional_note": None,
            "additional_preferences": None
        }
    ]
    response = client.post("/messages/batch", json=payload)
    assert response.status_code == 500
    assert "Gemini quota exceeded" in response.json()["detail"]


@patch("api.routers.messages.regenerate_responses")
def test_regenerate_message(mock_regenerate):
    """Test regenerating outreach message."""
    mock_regenerate.return_value = {
        "linkedin_url": "https://www.linkedin.com/in/gautamw",
        "generated_message": "Mocked regenerated message.",
        "generated_at": "2026-08-30 15:00:00"
    }
    payload = {
        "linkedin_url": "https://www.linkedin.com/in/gautamw",
        "additional_note": "Make it shorter",
        "additional_preferences": {
            "length": "short",
            "tone": "professional",
            "formality": "balanced",
            "directness": "direct",
            "style": "concise"
        }
    }
    response = client.post("/messages/regenerate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["generated_message"] == "Mocked regenerated message."
    assert data["status"] == "success"


@patch("api.routers.messages.regenerate_responses")
def test_regenerate_message_failure_bubbles_up(mock_regenerate):
    """Test that model failure during regeneration bubbles up as an HTTP error."""
    mock_regenerate.side_effect = RuntimeError("Gemini model overloaded")
    payload = {
        "linkedin_url": "https://www.linkedin.com/in/gautamw",
        "additional_note": "Make it shorter",
        "additional_preferences": None
    }
    response = client.post("/messages/regenerate", json=payload)
    assert response.status_code == 500
    assert "Gemini model overloaded" in response.json()["detail"]
