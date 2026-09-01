from fastapi import APIRouter, HTTPException
from services.helper import load_config

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
        config = load_config("prompts/user_preferences.yaml")
        return {
            "description": config.get("description", ""),
            "questions": config.get("questions", []),
            "default": config.get("default", ""),
            "rules": config.get("rules", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
