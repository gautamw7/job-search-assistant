from pathlib import Path
from unittest.mock import patch

import pytest
from job_search_assistant.services.resume import (
    get_resume_markdown,
    parse_resume_to_markdown,
    save_markdown,
    validate_markdown,
)


def test_validate_markdown_valid():
    """Test validate_markdown accepts valid resume content."""
    valid_text = (
        "This is a valid resume text for testing. "
        "Contact: testuser@example.com. "
        "Experience: Senior Software Engineer with 5 years of experience."
    )
    validate_markdown(valid_text)


def test_validate_markdown_too_short():
    """Test validate_markdown rejects short content."""
    with pytest.raises(ValueError, match="too short"):
        validate_markdown("Short text")


def test_validate_markdown_missing_keywords_and_contact():
    """Test validate_markdown rejects text without contact info or resume keywords."""
    invalid_text = "a" * 150
    with pytest.raises(ValueError, match="does not appear to be a valid resume"):
        validate_markdown(invalid_text)


def test_save_and_get_resume_markdown(tmp_path):
    """Test saving and getting resume markdown."""
    out_file = tmp_path / "resume.md"
    content = "## John Doe\nEmail: john@example.com\nExperience: Python Dev"
    save_markdown(content, output_path=out_file)
    assert out_file.exists()

    with patch("job_search_assistant.services.resume.RESUME_MD", out_file):
        retrieved = get_resume_markdown()
        assert retrieved == content


def test_get_resume_markdown_not_found():
    """Test get_resume_markdown raises FileNotFoundError when file doesn't exist."""
    fake_path = Path("/non/existent/resume.md")
    with (
        patch("job_search_assistant.services.resume.RESUME_MD", fake_path),
        pytest.raises(FileNotFoundError),
    ):
        get_resume_markdown()


def test_parse_resume_to_markdown_missing_pdf():
    """Test parse_resume_to_markdown raises FileNotFoundError for missing PDF."""
    with pytest.raises(FileNotFoundError):
        parse_resume_to_markdown("/non/existent/path.pdf")
