from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


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
    payload = {"content": "Friendly, warm, DS senior style.", "source": "questions"}
    response = client.post("/user-communication/update", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == payload["content"]
    assert data["source"] == payload["source"]

    get_response = client.get("/user-communication/")
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["content"] == payload["content"]
    assert get_data["source"] == payload["source"]


def test_update_user_communication_empty():
    """Test updating user communication style with empty text raises 400."""
    payload = {"content": ""}
    response = client.post("/user-communication/update", json=payload)
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]
