import asyncio
import os

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile

from app.core.logging import get_logger
from app.core.settings import DATA_DIR, RESUME_PDF
from app.services import structured_resume as structured
from app.services.resume import (
    check_resume_markdown,
    get_resume_markdown,
    parse_resume_to_markdown,
    save_markdown,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/resume",
    tags=["resume"],
    responses={404: {"description": "Not found"}},
)

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_MARKDOWN_CHARS = 200_000


@router.get("/")
def get_resume():
    if not check_resume_markdown():
        logger.info("resume not found")
        raise HTTPException(status_code=404, detail="Resume not found.")
    return Response(content=get_resume_markdown(), media_type="text/markdown")


@router.post("/")
async def upload_resume(file: UploadFile = File(...)):
    logger.info("resume upload start filename=%s", getattr(file, "filename", ""))

    contents = await file.read(MAX_PDF_BYTES + 1)
    if len(contents) > MAX_PDF_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"PDF is too large (max {MAX_PDF_BYTES // (1024 * 1024)} MB).",
        )
    # Trust the file's bytes, not the client-supplied content-type header.
    if not contents.startswith(b"%PDF"):
        logger.warning("resume upload rejected: not a pdf")
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Parse a temp copy first so a bad upload never destroys the current resume.
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = DATA_DIR / "resume.upload.pdf"
    await asyncio.to_thread(tmp_path.write_bytes, contents)
    try:
        await parse_resume_to_markdown(str(tmp_path))
        await asyncio.to_thread(os.replace, tmp_path, RESUME_PDF)
    except (ValueError, FileNotFoundError) as e:
        logger.warning("resume conversion rejected: %s", e)
        raise HTTPException(
            status_code=400, detail=str(e) or "Could not read this PDF."
        ) from e
    except Exception as e:
        logger.exception("resume conversion failed")
        raise HTTPException(
            status_code=400, detail="Could not read this PDF. Is it a valid file?"
        ) from e
    finally:
        tmp_path.unlink(missing_ok=True)

    logger.info("resume uploaded and converted successfully")
    return {"message": "Resume uploaded and converted to Markdown successfully."}


@router.post("/markdown")
async def save_resume_markdown(request: Request):
    try:
        body = await request.json()
    except ValueError:
        logger.warning("save markdown: invalid json")
        body = {}

    markdown_text = (
        body.get("raw_markdown", body.get("content", ""))
        if isinstance(body, dict)
        else ""
    )
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        logger.warning("save markdown rejected: empty content")
        raise HTTPException(status_code=400, detail="Markdown content cannot be empty.")
    if len(markdown_text) > MAX_MARKDOWN_CHARS:
        raise HTTPException(status_code=413, detail="Markdown content is too large.")

    try:
        await save_markdown(markdown_text)
    except OSError as e:
        logger.exception("save markdown failed")
        raise HTTPException(status_code=500, detail="Failed to save markdown.") from e
    logger.info("resume markdown saved len=%s", len(markdown_text))
    return {"message": "Resume markdown saved successfully."}


# ---- structured base resume (source of truth for tailoring) --------------------


def _structured_payload(state: dict | None) -> dict:
    if not state:
        raise HTTPException(
            status_code=404, detail="Structured resume not created yet."
        )
    current_hash = (
        structured.markdown_hash(get_resume_markdown())
        if check_resume_markdown()
        else None
    )
    return {
        "resume": state["resume"].model_dump(),
        "confirmed": state["confirmed"],
        "updated_at": state["updated_at"],
        # The PDF/Markdown changed since this was built: offer to rebuild it.
        "stale": current_hash is not None and current_hash != state["source_hash"],
    }


@router.get("/structured")
def get_structured_resume():
    return _structured_payload(structured.load())


@router.post("/structured/convert")
def convert_structured_resume():
    """Build (or rebuild) the structured resume from the current Markdown. Unconfirmed."""
    if not check_resume_markdown():
        raise HTTPException(status_code=400, detail="Upload your resume first.")
    markdown = get_resume_markdown()
    try:
        resume = structured.convert_markdown(markdown)
    except Exception as e:
        logger.exception("structured resume conversion failed")
        raise HTTPException(
            status_code=502, detail=f"Could not structure the resume: {e}"
        ) from e
    return _structured_payload(
        structured.save(resume, structured.markdown_hash(markdown), confirmed=False)
    )


@router.put("/structured")
def save_structured_resume(resume: structured.StructuredResume, confirm: bool = True):
    """Save the user's reviewed/edited version (confirmed by default)."""
    if not resume.contact.name and not resume.experience and not resume.education:
        raise HTTPException(status_code=400, detail="The resume looks empty.")
    source = (
        structured.markdown_hash(get_resume_markdown())
        if check_resume_markdown()
        else ""
    )
    return _structured_payload(structured.save(resume, source, confirmed=confirm))
