from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_get_personalization_config():
    """Test getting personalization config schema."""
    response = client.get("/personalization/config")
    assert response.status_code == 200
    data = response.json()
    assert "questions" in data
    assert "description" in data
