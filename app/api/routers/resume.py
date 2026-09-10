import asyncio
import json

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile

from app.services.logger import get_logger
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


@router.get("/")
async def get_resume():
    if not check_resume_markdown():
        logger.info("resume not found")
        raise HTTPException(status_code=404, detail="Resume not found.")

    logger.debug("resume retrieved")
    return Response(content=get_resume_markdown(), media_type="text/markdown")


@router.post("/")
async def upload_resume(file: UploadFile = File(...)):
    logger.info(
        "resume upload start filename=%s content_type=%s",
        getattr(file, "filename", ""),
        file.content_type,
    )
    if file.content_type != "application/pdf":
        logger.warning(
            "resume upload rejected non-pdf content_type=%s", file.content_type
        )
        return {"error": "Only PDF files are allowed."}

    contents = await file.read()

    from app.services.paths import DATA_DIR

    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = DATA_DIR / "resume.pdf"

    await asyncio.to_thread(pdf_path.write_bytes, contents)
    logger.info("resume pdf saved path=%s", pdf_path)

    try:
        await parse_resume_to_markdown(str(pdf_path))
        logger.info("resume uploaded and converted successfully")
        return {"message": "Resume uploaded and converted to Markdown successfully."}
    except (ValueError, FileNotFoundError) as e:
        logger.exception("resume conversion failed")
        raise HTTPException(
            status_code=400, detail=str(e) or "Only PDF files are allowed."
        )


@router.post("/markdown")
async def save_resume_markdown(request: Request):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        logger.warning("save markdown: invalid json")
        body = {}

    markdown_text = body.get("raw_markdown", body.get("content", ""))
    if not markdown_text:
        logger.warning("save markdown rejected: empty content")
        raise HTTPException(status_code=400, detail="Markdown content cannot be empty.")

    try:
        await save_markdown(markdown_text)
        logger.info("resume markdown saved len=%s", len(markdown_text))
        return {"message": "Resume markdown saved successfully."}
    except (ValueError, OSError):
        logger.exception("save markdown failed")
        raise HTTPException(status_code=400, detail="Failed to save markdown.")
