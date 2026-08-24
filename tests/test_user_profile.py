import pytest
from pathlib import Path

from backend.database.repository.user_profile import (
    extract_resume_markdown,
    convert_resume_to_markdown,
    save_user_profile,
)


def test_extract_resume_markdown_missing_file():
    """Test that extracting markdown from a non-existent PDF raises an error."""
    with pytest.raises(Exception) as excinfo:
        extract_resume_markdown("/nonexistent/path/to/resume.pdf")
    assert "does not exist" in str(excinfo.value).lower()


def test_convert_resume_to_markdown_with_sections():
    """Test that resume text with section headings is correctly converted to Markdown."""
    raw_text = (
        "John Doe\n\nEducation\nBS Computer Science\n\nExperience\nJob at Company\n"
    )
    markdown = convert_resume_to_markdown(raw_text)
    assert "# John Doe" in markdown
    assert "## Education" in markdown
    assert "## Experience" in markdown
    assert "BS Computer Science" in markdown


def test_convert_resume_to_markdown_empty():
    """Test that empty text results in empty markdown."""
    assert convert_resume_to_markdown("") == ""
    assert convert_resume_to_markdown("   ") == ""


def test_extract_resume_markdown_real_pdf():
    """Test extraction from the actual PDF in the project (if it exists)."""
    pdf_path = "backend/data/Gautam_Warvatkar_Resume.pdf"
    if not Path(pdf_path).exists():
        pytest.skip("Real PDF file not found")
    markdown = extract_resume_markdown(pdf_path)
    assert isinstance(markdown, str)
    assert len(markdown) > 0

    # Check some expected markdown elements exist after conversion
    assert "## Experience" in markdown or "experience" in markdown.lower()


class TestUserProfileRepository:
    def test_save_user_profile(self, temp_db_file):
        """Test that user profile can be saved and retrieved."""
        personality = "# Gautam Warvatkar\nData Scientist"
        resume = "# Resume\n## Experience\nWork at Syngenta"

        save_user_profile(personality, resume)

        # Verify by reading directly
        import sqlite3

        conn = sqlite3.connect(str(temp_db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT personality_markdown, resume_markdown FROM user_profile")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == personality
        assert row[1] == resume

    def test_user_profile_row_inserted(self, temp_db_file):
        """Test that user_profile row can be saved and counted."""
        import sqlite3

        save_user_profile("pers1", "res1")

        conn = sqlite3.connect(str(temp_db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT rowid, COUNT(*) as cnt FROM user_profile")
        row = cursor.fetchone()
        conn.close()

        # There should be at least one row
        assert row is not None
        assert row[1] >= 1
