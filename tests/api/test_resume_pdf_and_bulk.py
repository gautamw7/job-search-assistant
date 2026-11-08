from fastapi.testclient import TestClient

from app.app import app
from app.core.settings import RESUME_PDF

client = TestClient(app)


def test_uploaded_resume_pdf_is_served_for_preview():
    RESUME_PDF.parent.mkdir(parents=True, exist_ok=True)
    RESUME_PDF.write_bytes(b"%PDF-1.4 fake")
    r = client.get("/resume/pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    RESUME_PDF.unlink()
    assert client.get("/resume/pdf").status_code == 404


def test_bulk_mark_drafted_as_sent():
    from app.services.generation import save_generated_messages

    urls = [f"https://www.linkedin.com/in/bulk{i}" for i in range(3)]
    save_generated_messages(
        {
            u: {
                "generations": [
                    {"generated_message": "hi", "generated_at": "2026-11-01 10:00:00"}
                ]
            }
            for u in urls
        }
    )
    r = client.post(
        "/tracker/bulk",
        json={
            "linkedin_urls": urls + ["https://www.linkedin.com/in/ghost"],
            "status": "sent",
        },
    )
    assert r.status_code == 200
    assert r.json() == {"updated": 3, "missing": ["https://www.linkedin.com/in/ghost"]}
    statuses = [
        c["status"]
        for c in client.get("/tracker/").json()["contacts"]
        if c["linkedin_url"] in urls
    ]
    assert statuses == ["sent", "sent", "sent"]
    assert (
        client.post(
            "/tracker/bulk", json={"linkedin_urls": [], "status": "sent"}
        ).status_code
        == 400
    )
