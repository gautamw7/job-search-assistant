"""Tailored resumes per job: create (AI), edit, build PDF, download/export."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from app.core.logging import get_logger
from app.services import latex, tailor
from app.services.structured_resume import StructuredResume

logger = get_logger(__name__)
router = APIRouter(prefix="/tailored", tags=["tailored"])


class CreateRequest(BaseModel):
    job_id: str


class ExportRequest(BaseModel):
    kind: str = "pdf"


@router.get("/compiler")
def compiler_status():
    found = latex.find_compiler()
    return {"available": found is not None, "compiler": found[0] if found else None}


@router.get("")
def list_tailored(job_id: str | None = None):
    return tailor.list_for_job(job_id)


@router.post("")
def create_tailored(req: CreateRequest):
    try:
        return tailor.create(req.job_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except tailor.TailorError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("tailoring failed job=%s", req.job_id)
        raise HTTPException(status_code=502, detail=f"Tailoring failed: {e}") from e


def _get_or_404(tailored_id: str) -> dict:
    try:
        return tailor.get(tailored_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/{tailored_id}")
def get_tailored(tailored_id: str):
    return _get_or_404(tailored_id)


@router.put("/{tailored_id}")
def update_tailored(tailored_id: str, resume: StructuredResume, recheck: bool = False):
    _get_or_404(tailored_id)
    try:
        return tailor.update(tailored_id, resume, recheck=recheck)
    except tailor.TailorError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{tailored_id}")
def delete_tailored(tailored_id: str):
    _get_or_404(tailored_id)
    tailor.delete(tailored_id)
    return {"deleted": True}


@router.get("/{tailored_id}/tex")
def download_tex(tailored_id: str):
    _get_or_404(tailored_id)
    return PlainTextResponse(
        tailor.tex_for(tailored_id),
        media_type="application/x-tex",
        headers={
            "Content-Disposition": f'attachment; filename="{tailor.export_filename(tailored_id, "tex")}"'
        },
    )


@router.post("/{tailored_id}/pdf")
def build_pdf(tailored_id: str):
    _get_or_404(tailored_id)
    try:
        return tailor.build_pdf(tailored_id)
    except latex.CompileError as e:
        raise HTTPException(
            status_code=422, detail={"message": str(e), "log": e.log}
        ) from e


@router.get("/{tailored_id}/pdf")
def get_pdf(tailored_id: str):
    _get_or_404(tailored_id)
    try:
        path = tailor.pdf_path(tailored_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=tailor.export_filename(tailored_id, "pdf"),
    )


@router.post("/{tailored_id}/export")
def export(tailored_id: str, req: ExportRequest):
    _get_or_404(tailored_id)
    if req.kind not in ("pdf", "tex"):
        raise HTTPException(status_code=400, detail="kind must be pdf or tex")
    try:
        target = tailor.export_to_downloads(tailored_id, req.kind)
    except LookupError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"path": str(target)}
