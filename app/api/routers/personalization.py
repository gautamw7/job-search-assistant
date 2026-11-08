from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.core.settings import PROMPTS_DIR
from app.infra.config import load_config

logger = get_logger(__name__)

router = APIRouter(
    prefix="/personalization",
    tags=["personalization"],
)


@router.get("/config")
def get_personalization_config():
    """
    Retrieve available personalization options and questions for the frontend UI.
    """
    try:
        config = load_config(str(PROMPTS_DIR / "user_preferences.yaml"))
        logger.debug(
            "personalization config served questions=%s",
            len(config.get("questions", [])),
        )
        return {
            "description": config.get("description", ""),
            "questions": config.get("questions", []),
            "default": config.get("default", ""),
            "rules": config.get("rules", []),
        }
    except Exception as e:
        logger.exception("failed to load personalization config err=%s", e)
        raise HTTPException(status_code=500, detail=str(e))
