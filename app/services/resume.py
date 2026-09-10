import asyncio
import re
from pathlib import Path

import pymupdf4llm

from app.services.logger import get_logger
from app.services.paths import RESUME_MD

logger = get_logger(__name__)


def validate_markdown(markdown_text: str) -> None:
    text = markdown_text.strip()
    if not text or len(text) < 100:
        raise ValueError(
            "Extracted text is too short to be a valid resume. Please upload a full resume PDF."
        )

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


async def parse_resume_to_markdown(pdf_path: str):
    if not Path(pdf_path).exists():
        logger.error("pdf not found path=%s", pdf_path)
        raise FileNotFoundError(f"PDF file not found at {pdf_path}")

    if check_resume_markdown():
        logger.warning("markdown file exists, will be overwritten path=%s", RESUME_MD)

    logger.info("extracting markdown from pdf path=%s", pdf_path)
    markdown_text = await asyncio.to_thread(pymupdf4llm.to_markdown, pdf_path)
    validate_markdown(markdown_text)

    logger.info(
        "successfully extracted markdown from %s len=%s", pdf_path, len(markdown_text)
    )
    await save_markdown(markdown_text)


def check_resume_markdown() -> bool:
    return RESUME_MD.exists()


async def save_markdown(markdown_text: str, output_path: Path = RESUME_MD) -> None:
    output_path = Path(output_path)
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        logger.warning("overwriting existing file path=%s", output_path)

    await asyncio.to_thread(output_path.write_text, markdown_text, encoding="utf-8")
    logger.info("markdown resume saved path=%s len=%s", output_path, len(markdown_text))


def get_resume_markdown() -> str:
    if not RESUME_MD.exists():
        raise FileNotFoundError(f"Resume markdown not found at {RESUME_MD}")
    return RESUME_MD.read_text(encoding="utf-8")
