from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Response
from services.resume import check_resume_markdown, get_resume_markdown, parse_resume_to_markdown, save_markdown, DATA_DIR, RESUME_PDF
import os

router = APIRouter(
    prefix="/resume",
    tags=["resume"],
    responses={404: {"description": "Not found"}},
)

@router.get("/")
async def get_resume():
    if not check_resume_markdown():
        raise HTTPException(
            status_code=404,
            detail="Resume not found."
        )

    return Response(
        content=get_resume_markdown(),
        media_type="text/markdown"
    )

@router.post("/")
async def upload_resume(file: UploadFile = File(...)):
    """
    Upload a resume PDF and convert it to Markdown.
    """
    if file.content_type != "application/pdf":
        return {"error": "Only PDF files are allowed."}

    # Save the uploaded file in data directory
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = RESUME_PDF
    with open(pdf_path, "wb") as f:
        f.write(await file.read())

    # Convert the PDF to Markdown
    try:
        parse_resume_to_markdown(str(pdf_path))
        return {"message": "Resume uploaded and converted to Markdown successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e) or "Only PDF files are allowed."
        )

@router.post("/markdown")
async def save_resume_markdown(request: Request):
    """
    Save raw resume markdown directly.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    markdown_text = body.get("raw_markdown", body.get("content", ""))
    if not markdown_text:
        raise HTTPException(status_code=400, detail="Markdown content cannot be empty.")

    try:
        save_markdown(markdown_text)
        return {"message": "Resume markdown saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
