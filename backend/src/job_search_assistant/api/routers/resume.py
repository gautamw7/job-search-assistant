from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile
from job_search_assistant.services.logger import get_logger
from job_search_assistant.services.resume import (
    DATA_DIR,
    RESUME_PDF,
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
    """
    Upload a resume PDF and convert it to Markdown.
    """
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

    # Save the uploaded file in data directory
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = RESUME_PDF
    with open(pdf_path, "wb") as f:
        f.write(await file.read())
    logger.info("resume pdf saved path=%s", pdf_path)

    # Convert the PDF to Markdown
    try:
        parse_resume_to_markdown(str(pdf_path))
        logger.info("resume uploaded and converted successfully")
        return {"message": "Resume uploaded and converted to Markdown successfully."}
    except Exception as e:
        logger.exception("resume conversion failed err=%s", e)
        raise HTTPException(
            status_code=400, detail=str(e) or "Only PDF files are allowed."
        )


@router.post("/markdown")
async def save_resume_markdown(request: Request):
    """
    Save raw resume markdown directly.
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.warning("save markdown: invalid json err=%s", e)
        body = {}

    markdown_text = body.get("raw_markdown", body.get("content", ""))
    if not markdown_text:
        logger.warning("save markdown rejected: empty content")
        raise HTTPException(status_code=400, detail="Markdown content cannot be empty.")

    try:
        save_markdown(markdown_text)
        logger.info("resume markdown saved len=%s", len(markdown_text))
        return {"message": "Resume markdown saved successfully."}
    except Exception as e:
        logger.exception("save markdown failed err=%s", e)
        raise HTTPException(status_code=400, detail=str(e))
