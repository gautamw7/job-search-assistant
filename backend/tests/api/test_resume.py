from unittest.mock import patch

from fastapi.testclient import TestClient
from job_search_assistant.api.main import app

client = TestClient(app)


def test_resume_get():
    """Test getting resume markdown."""
    response = client.get("/resume/")
    assert response.status_code in [200, 404, 204]


@patch("job_search_assistant.api.routers.resume.check_resume_markdown")
def test_get_resume_not_found(mock_check):
    """Test GET /resume/ returns 404 when resume markdown is missing."""
    mock_check.return_value = False
    response = client.get("/resume/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Resume not found."


@patch("job_search_assistant.api.routers.resume.check_resume_markdown")
@patch("job_search_assistant.api.routers.resume.get_resume_markdown")
def test_get_resume_success(mock_get_md, mock_check):
    """Test GET /resume/ returns markdown text when resume exists."""
    mock_check.return_value = True
    mock_get_md.return_value = "# John Doe\nSoftware Engineer"
    response = client.get("/resume/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.text == "# John Doe\nSoftware Engineer"


def test_upload_resume_invalid_file_type():
    """Test uploading non-PDF file to /resume/ returns error message."""
    files = {"file": ("test.txt", b"plain text content", "text/plain")}
    response = client.post("/resume/", files=files)
    assert response.status_code == 200
    assert response.json() == {"error": "Only PDF files are allowed."}


@patch("job_search_assistant.api.routers.resume.parse_resume_to_markdown")
def test_upload_resume_pdf_success(mock_parse):
    """Test uploading PDF file converts it to markdown successfully."""
    pdf_bytes = b"%PDF-1.4 test pdf content"
    files = {"file": ("resume.pdf", pdf_bytes, "application/pdf")}
    response = client.post("/resume/", files=files)
    assert response.status_code == 200
    assert "uploaded and converted" in response.json()["message"]
    mock_parse.assert_called_once()


def test_save_resume_markdown_success():
    """Test saving raw markdown resume directly via POST /resume/markdown."""
    with patch("job_search_assistant.api.routers.resume.save_markdown") as mock_save:
        payload = {"raw_markdown": "# Jane Doe Resume"}
        response = client.post("/resume/markdown", json=payload)
        assert response.status_code == 200
        assert response.json()["message"] == "Resume markdown saved successfully."
        mock_save.assert_called_once_with("# Jane Doe Resume")


def test_save_resume_markdown_empty():
    """Test POST /resume/markdown rejects empty markdown content."""
    payload = {"raw_markdown": ""}
    response = client.post("/resume/markdown", json=payload)
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]
