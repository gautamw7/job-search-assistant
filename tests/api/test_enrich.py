from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)

SAMPLE_URL = "https://www.linkedin.com/in/test-enrich"
SAMPLE_PROFILE = {
    "card_info": {
        "id": "test-enrich",
        "name": "Test Enrich",
        "url": SAMPLE_URL,
        "position": "Senior Engineer",
        "current_company_name": "TestCorp",
        "location": "Bengaluru",
        "followers": 123,
        "connections": 500,
    },
    "content": {
        "about": "About Test Enrich",
        "experience": None,
        "education": [],
    },
    "activity": {
        "hiring": [{"title": "We are hiring", "link": "https://example.com/1"}],
        "dropped": [{"title": "Normal post", "link": "https://example.com/2"}],
    },
    "discovery": {
        "people_also_viewed": [
            {
                "name": "Jane Doe",
                "profile_link": "https://linkedin.com/in/jane",
                "about": "Engineer",
                "location": "Bengaluru",
            }
        ]
    },
    "dropped_fields": {"extra": "value"},
}


def _mock_store(data):
    return {SAMPLE_URL: data}


@patch("app.api.routers.enrich._load_enriched_store")
def test_get_card_info_success(mock_load):
    mock_load.return_value = _mock_store(SAMPLE_PROFILE)
    response = client.get(f"/enrich/{SAMPLE_URL}/card")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Enrich"
    assert response.json()["current_company_name"] == "TestCorp"


@patch("app.api.routers.enrich._load_enriched_store")
def test_get_content_info_success(mock_load):
    mock_load.return_value = _mock_store(SAMPLE_PROFILE)
    response = client.get(f"/enrich/{SAMPLE_URL}/content")
    assert response.status_code == 200
    assert response.json()["about"] == "About Test Enrich"


@patch("app.api.routers.enrich._load_enriched_store")
def test_get_activity_info_success(mock_load):
    mock_load.return_value = _mock_store(SAMPLE_PROFILE)
    response = client.get(f"/enrich/{SAMPLE_URL}/activity")
    assert response.status_code == 200
    data = response.json()
    assert "hiring" in data and "dropped" in data
    assert len(data["hiring"]) == 1
    assert data["hiring"][0]["title"] == "We are hiring"
    assert len(data["dropped"]) == 1


@patch("app.api.routers.enrich._load_enriched_store")
def test_get_discovery_info_success(mock_load):
    mock_load.return_value = _mock_store(SAMPLE_PROFILE)
    response = client.get(f"/enrich/{SAMPLE_URL}/discovery")
    assert response.status_code == 200
    assert len(response.json()["people_also_viewed"]) == 1
    assert response.json()["people_also_viewed"][0]["name"] == "Jane Doe"


@patch("app.api.routers.enrich._load_enriched_store")
def test_get_enriched_profile_success(mock_load):
    mock_load.return_value = _mock_store(SAMPLE_PROFILE)
    response = client.get(f"/enrich/{SAMPLE_URL}")
    assert response.status_code == 200
    data = response.json()
    assert "card_info" in data
    assert "content" in data
    assert "activity" in data
    assert "discovery" in data


@patch("app.api.routers.enrich._load_enriched_store")
def test_enrich_not_found(mock_load):
    mock_load.return_value = {}
    response = client.get(f"/enrich/{SAMPLE_URL}/card")
    assert response.status_code == 404
    assert "Profile not found" in response.json()["detail"]


@patch("app.api.routers.enrich._load_enriched_store")
def test_enrich_legacy_string_format(mock_load):
    mock_load.return_value = {SAMPLE_URL: "legacy string data"}
    response = client.get(f"/enrich/{SAMPLE_URL}/card")
    assert response.status_code == 404
    assert "re-enrich required" in response.json()["detail"]


def test_enrich_store_not_found():
    # Force _load_enriched_store to see missing file
    # Patch exists check directly
    with patch(
        "app.api.routers.enrich._load_enriched_store",
        side_effect=Exception("store missing"),
    ):
        # Use get to trigger load, but we mock the loader to raise 404
        pass
    # Test via direct endpoint with mocked loader returning 404 store
    with patch(
        "app.api.routers.enrich._load_enriched_store",
        side_effect=__import__("fastapi").HTTPException(
            status_code=404, detail="Enrich store not found"
        ),
    ):
        response = client.get(f"/enrich/{SAMPLE_URL}/card")
        assert response.status_code == 404
