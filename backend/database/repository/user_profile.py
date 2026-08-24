from pypdf import PdfReader
from pathlib import Path
from backend.database.sql_connection import create_connection
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def validate_pdf_file(pdf_path: str) -> list:
    try:
        path = Path(pdf_path)

        if not path.is_file():
            logger.error("PDF file does not exist: %s", pdf_path)
            raise ValueError(f"PDF file does not exist: {pdf_path}")

        if not path.suffix.lower() == ".pdf":
            logger.error("File is not a PDF file: %s", pdf_path)
            raise ValueError(f"File is not a PDF file: {pdf_path}")

        reader = PdfReader(pdf_path)
        if not reader.pages:
            logger.error("PDF file is empty: %s", pdf_path)
            raise ValueError(f"PDF file is empty: {pdf_path}")

        return reader.pages

    except Exception as e:
        logger.error("Error validating PDF file: %s", e)
        raise ValueError(f"Error validating PDF file: {e}")


SECTION_HEADINGS = {
    "education": "Education",
    "experience": "Experience",
    "work experience": "Experience",
    "skills": "Skills",
    "projects": "Projects",
    "certifications": "Certifications",
    "summary": "Summary",
    "profile": "Profile",
}


def convert_resume_to_markdown(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    markdown = []

    for index, line in enumerate(lines):
        normalized = line.lower().strip()

        if index == 0:
            markdown.append(f"# {line}")
            continue

        if normalized in SECTION_HEADINGS:
            markdown.append(f"## {SECTION_HEADINGS[normalized]}")
            continue

        markdown.append(line)

    return "\n\n".join(markdown)


def extract_resume_markdown(pdf_path: str) -> str:
    """
    Create a markdown representation of the resume from the PDF file.

    Args:
        pdf_path (str): The path to the PDF file.
    """
    try:
        render_pages = validate_pdf_file(pdf_path)
        pages = []
        for page in render_pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())

        if not pages:
            logger.error("No text found in PDF file: %s", pdf_path)
            raise ValueError(f"No text found in PDF file: {pdf_path}")

        text = "\n\n".join(pages)
        markdown = convert_resume_to_markdown(text)

        if not markdown.strip():
            logger.error("Failed to convert resume to markdown: %s", pdf_path)
            raise ValueError(f"Failed to convert resume to markdown: {pdf_path}")

        return markdown
    except Exception as e:
        logger.error("Error extracting resume markdown: %s", e)
        raise ValueError(f"Error extracting resume markdown: {e}")


def save_user_profile(personality_markdown: str, resume_markdown: str):
    """
    Save the user profile data to the database.

    Args:
        personality_markdown (str): The personality markdown text.
        resume_markdown (str): The resume markdown text.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO user_profile (personality_markdown, resume_markdown)
            VALUES (?, ?)
        """
        cursor.execute(query, (personality_markdown, resume_markdown))
        conn.commit()
        logger.info("User profile saved successfully.")
    except Exception as e:
        logger.error("Error saving user profile: %s", e)
        raise ValueError(f"Error saving user profile: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    # Example usage
    pdf_path = "backend/data/Gautam_Warvatkar_Resume.pdf"
    markdown_path = "backend/data/personality_markdown.md"
    try:
        resume_markdown = extract_resume_markdown(pdf_path)
        personality_markdown = ""
        with open(markdown_path, "r") as f:
            personality_markdown = f.read()
        save_user_profile(personality_markdown, resume_markdown)
    except Exception as e:
        logger.error("An error occurred: %s", e)
