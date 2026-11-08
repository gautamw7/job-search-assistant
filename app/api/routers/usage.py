from fastapi import APIRouter, HTTPException

from app.api.schemas import SettingsUpdate
from app.services import usage

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/")
def get_usage():
    """This month's and today's usage, estimated cost, prices and limits."""
    return usage.summary()


@router.put("/settings")
def update_settings(req: SettingsUpdate):
    try:
        usage.save_settings(req.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return usage.summary()
