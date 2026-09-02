from fastapi.testclient import TestClient
from job_search_assistant.api.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test that the root endpoint returns 200 or 404."""
    response = client.get("/")
    assert response.status_code in [200, 404]
