from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.app import app

client = TestClient(app)


def _resp(code):
    r = MagicMock()
    r.status_code = code
    return r


def test_adzuna_save_verify_and_mask():
    with patch("app.api.routers.config.requests.get", return_value=_resp(200)) as get:
        r = client.post(
            "/config/adzuna", json={"app_id": "abcd1234", "app_key": "key-0123456789"}
        )
    assert r.status_code == 200 and r.json()["verified"] is True
    assert get.call_args.kwargs["params"]["app_id"] == "abcd1234"
    with patch(
        "app.services.secrets.keyring.get_password",
        side_effect=lambda s, u: {
            "jobsearchassistant_adzuna_app_id": "abcd1234",
            "jobsearchassistant_adzuna_app_key": "key-0123456789",
        }.get(s),
    ):
        masked = client.get("/config/adzuna").json()["masked"]
    assert "key-0123456789" not in masked and "/" in masked


def test_adzuna_invalid_and_offline():
    with patch("app.api.routers.config.requests.get", return_value=_resp(401)):
        assert (
            client.post(
                "/config/adzuna", json={"app_id": "a", "app_key": "b"}
            ).status_code
            == 400
        )
    with patch("app.api.routers.config.requests.get", side_effect=OSError("offline")):
        r = client.post("/config/adzuna", json={"app_id": "a", "app_key": "b"})
    assert r.status_code == 200 and r.json()["verified"] is False


def test_apify_token_checked_with_bearer_header():
    with patch("app.api.routers.config.requests.get", return_value=_resp(200)) as get:
        r = client.post("/config/apify", json={"api_key": "apify_api_123456"})
    assert r.status_code == 200
    assert get.call_args.kwargs["headers"]["Authorization"] == "Bearer apify_api_123456"
    with patch("app.api.routers.config.requests.get", return_value=_resp(401)):
        assert (
            client.post("/config/apify", json={"api_key": "apify_api_bad"}).status_code
            == 400
        )
    assert client.get("/config/apify").status_code == 404  # null keyring in tests
