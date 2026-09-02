import os
import re
from pathlib import Path

import pymupdf4llm
from job_search_assistant.services.logger import get_logger
from job_search_assistant.services.paths import RESUME_MD

logger = get_logger(__name__)


def validate_markdown(markdown_text: str) -> None:
    """
    Validate the extracted Markdown text.
    Raises ValueError if the Markdown is invalid or doesn't look like a resume.
    """
    text = markdown_text.strip()
    if not text or len(text) < 100:
        raise ValueError(
            "Extracted text is too short to be a valid resume. Please upload a full resume PDF."
        )

    # Check for contact info (email or phone) or common resume sections
    email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    phone_pattern = re.compile(r"(\+\d{1,3}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
    has_contact = email_pattern.search(text) or phone_pattern.search(text)

    keywords = [
        "experience",
        "education",
        "skills",
        "projects",
        "work",
        "employment",
        "history",
    ]
    has_keywords = any(kw in text.lower() for kw in keywords)

    if not has_contact and not has_keywords:
        raise ValueError(
            "The uploaded document does not appear to be a valid resume (missing contact info or standard resume sections). Please upload a valid resume PDF."
        )


def parse_resume_to_markdown(pdf_path: str):
    """Extracts clean Markdown text from a resume PDF using pymupdf4llm."""
    if not os.path.exists(pdf_path):
        logger.error("pdf not found path=%s", pdf_path)
        raise FileNotFoundError(f"PDF file not found at {pdf_path}")

    if check_resume_markdown():
        logger.warning("markdown file exists, will be overwritten path=%s", RESUME_MD)

    logger.info("extracting markdown from pdf path=%s", pdf_path)
    markdown_text = pymupdf4llm.to_markdown(pdf_path)
    validate_markdown(markdown_text)

    logger.info(
        "successfully extracted markdown from %s len=%s", pdf_path, len(markdown_text)
    )
    save_markdown(markdown_text)


def check_resume_markdown() -> bool:
    """
    Check markdown file exists
    """
    return RESUME_MD.exists()


def save_markdown(markdown_text: str, output_path: Path = RESUME_MD) -> None:
    """
    Save the extracted Markdown text to a file.
    """
    output_path = Path(output_path)
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        logger.warning("overwriting existing file path=%s", output_path)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    logger.info("markdown resume saved path=%s len=%s", output_path, len(markdown_text))


def get_resume_markdown() -> str:
    """
    Get the resume in Markdown format.
    """
    if not RESUME_MD.exists():
        raise FileNotFoundError(f"Resume markdown not found at {RESUME_MD}")
    with open(RESUME_MD, "r", encoding="utf-8") as f:
        return f.read()
