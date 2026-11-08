from fastapi.testclient import TestClient

from app.app import create_app


def test_token_required_when_configured(monkeypatch):
    monkeypatch.setenv("JOB_SEARCH_API_TOKEN", "s3cret")
    client = TestClient(create_app())

    assert client.get("/health").status_code == 200  # liveness stays open
    assert client.get("/resume/").status_code == 401
    assert client.get("/resume/", headers={"X-API-Token": "wrong"}).status_code == 401
    ok = client.get("/resume/", headers={"X-API-Token": "s3cret"})
    assert ok.status_code in (200, 404)


def test_cors_allows_app_origin_but_not_random_sites():
    client = TestClient(create_app())
    good = client.get("/health", headers={"Origin": "tauri://localhost"})
    assert good.headers.get("access-control-allow-origin") == "tauri://localhost"
    bad = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in bad.headers
