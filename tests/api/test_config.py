from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


@patch("app.api.routers.config.test_brightdata_connection")
@patch("app.services.secrets.keyring.set_password")
def test_store_brightdata_credentials_success(mock_set_pwd, mock_test_conn):
    """Test successfully storing BrightData credentials."""
    response = client.post(
        "/config/brightdata", json={"api_key": "bright_test_key_123"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "BrightData credentials stored successfully."
    mock_test_conn.assert_called_once_with("bright_test_key_123")
    mock_set_pwd.assert_called_once_with(
        "jobsearchassistant_brightdata", "api_key", "bright_test_key_123"
    )


@patch("app.api.routers.config.test_brightdata_connection")
def test_store_brightdata_credentials_connection_failure(mock_test_conn):
    """Test storing BrightData credentials fails if connection test fails."""
    from fastapi import HTTPException

    mock_test_conn.side_effect = HTTPException(
        status_code=500, detail="Connection test failed"
    )
    response = client.post("/config/brightdata", json={"api_key": "bad_key"})
    assert response.status_code == 500


@patch("app.api.routers.config.test_gemini_connection")
@patch("app.services.secrets.keyring.set_password")
def test_store_gemini_credentials_success(mock_set_pwd, mock_test_conn):
    """Test successfully storing Gemini credentials."""
    response = client.post("/config/gemini", json={"api_key": "gemini_test_key_123"})
    assert response.status_code == 200
    assert response.json()["message"] == "Gemini credentials stored successfully."
    mock_test_conn.assert_called_once_with("gemini_test_key_123")
    mock_set_pwd.assert_called_once_with(
        "jobsearchassistant_gemini", "api_key", "gemini_test_key_123"
    )


@patch("app.services.secrets.keyring.get_password")
def test_get_brightdata_credentials_success(mock_get_pwd):
    """Test retrieving stored BrightData credentials (masked)."""
    mock_get_pwd.return_value = "stored_bright_key"
    response = client.get("/config/brightdata")
    assert response.status_code == 200
    assert "masked" in response.json()
    assert response.json()["masked"] == "stor********_key"
    assert response.json()["exists"] is True
    assert response.json()["api_key"] == "stor********_key"
    assert response.json()["api_key"] != "stored_bright_key"


@patch("app.services.secrets.keyring.get_password")
def test_get_brightdata_credentials_not_found(mock_get_pwd):
    """Test retrieving BrightData credentials when none are stored."""
    mock_get_pwd.return_value = None
    with (
        patch("app.services.secrets._get_local_secret", return_value=None),
        patch("os.getenv", return_value=None),
    ):
        response = client.get("/config/brightdata")
    assert response.status_code == 404
    assert response.json()["detail"] == "Credentials not found."


@patch("app.services.secrets.keyring.get_password")
def test_get_gemini_credentials_success(mock_get_pwd):
    """Test retrieving stored Gemini credentials (masked)."""
    mock_get_pwd.return_value = "stored_gemini_key"
    response = client.get("/config/gemini")
    assert response.status_code == 200
    assert response.json()["masked"] == "stor********_key"
    assert response.json()["exists"] is True


@patch("app.api.routers.config.get_secure_key")
@patch("app.api.routers.config.test_brightdata_connection")
def test_test_stored_brightdata_credentials_success(mock_test_conn, mock_get_key):
    """Test testing stored BrightData credentials successfully."""
    mock_get_key.return_value = "stored_bright_key"
    response = client.post("/config/brightdata/test")
    assert response.status_code == 200
    assert response.json()["message"] == "BrightData API key is valid and working."
    mock_test_conn.assert_called_once_with("stored_bright_key")


@patch("app.api.routers.config.get_secure_key")
def test_test_stored_brightdata_credentials_not_found(mock_get_key):
    """Test testing stored BrightData credentials when none are stored."""
    mock_get_key.return_value = None
    response = client.post("/config/brightdata/test")
    assert response.status_code == 404
    assert response.json()["detail"] == "Credentials not found."


@patch("app.api.routers.config.get_secure_key")
@patch("app.api.routers.config.test_gemini_connection")
def test_test_stored_gemini_credentials_success(mock_test_conn, mock_get_key):
    """Test testing stored Gemini credentials successfully."""
    mock_get_key.return_value = "stored_gemini_key"
    response = client.post("/config/gemini/test")
    assert response.status_code == 200
    assert response.json()["message"] == "Gemini API key is valid and working."
    mock_test_conn.assert_called_once_with("stored_gemini_key")
