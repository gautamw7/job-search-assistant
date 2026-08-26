from pypdf import PdfReader
from pathlib import Path
from backend.database.repository.enrichments import get_latest_enrichment
from backend.database.repository.user_profile import get_user_profile
from backend.utils.logger import get_logger
from backend.utils.helper import load_config


logger = get_logger(__name__)


def build_resources(
    linkedin_url: str, user_note: str, message_personalization: dict
) -> dict:
    """
    Build the necessary resources for generating a prompt based on the provided LinkedIn URL, user note, and message personalization.
    Raises exceptions on failure instead of returning a status dictionary.
    """
    logger.info("Building resources for LinkedIn URL: %s", linkedin_url)

    # This will raise an exception if enrichment data is missing or lookup fails
    brightdata_enrich_data = get_latest_enrichment(linkedin_url)
    if not brightdata_enrich_data:
        logger.warning("No enrichment data found for LinkedIn URL: %s", linkedin_url)
        raise LookupError(
            f"Enrichment data not found for LinkedIn URL: {linkedin_url}. Please enrich the profile first."
        )

    logger.info("Enrichment data retrieved for LinkedIn URL: %s", linkedin_url)

    user_profile = get_user_profile(linkedin_url)
    if not user_profile:
        raise LookupError(
            "User profile/resume not found. Please configure your profile first."
        )

    user_preference = process_message_personalization(message_personalization)

    input_data = {
        "user_resume": user_profile.get("resume_markdown", ""),
        "user_communication_style": user_profile.get("communication", ""),
        "user_preferences": user_preference,
        "recipient_enrich_data": brightdata_enrich_data,
        "user_notes": user_note,
    }

    return input_data


def process_message_personalization(message_personalization: dict) -> str:
    """
    Convert user message preferences into an LLM-friendly format.

    Uses the configured default preferences when no preferences are provided.
    """
    try:
        if not message_personalization:
            user_preferences_config = load_config("user_preferences")
            return user_preferences_config.get("default", "")

        preferences = [
            f"{key}: {value}" for key, value in message_personalization.items()
        ]

        return "\n".join(preferences)

    except Exception:
        logger.exception("Error processing message personalization")
        raise


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
