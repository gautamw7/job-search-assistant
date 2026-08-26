from fastapi import APIRouter
from backend.utils.logger import get_logger
from backend.database.repository.outreach_messages import get_latest_outreach_message
from backend.clients.litellm import LiteLLMClient

logger = get_logger(__name__)

router = APIRouter(prefix="/generation", tags=["Generation"])


@router.get("/")
def get_outreach_message(linked_url: str) -> dict:
    """
    Retrieve the latest outreach message for a given LinkedIn URL.
    """
    if not linked_url:
        raise ValueError("LinkedIn URL cannot be empty.")

    logger.info("Retrieving latest outreach message for LinkedIn URL: %s", linked_url)
    latest_content = get_latest_outreach_message(linked_url)
    return {
        "success": True,
        "status_code": 200,
        "result": latest_content,
    }


@router.post("/regenerate")
def regenerate_outreach_message(
    linkedin_url: str, user_note: str, message_personalization: dict
) -> dict:
    """
    Regenerate the outreach message for a given LinkedIn URL based on the provided user note.
    """
    if not linkedin_url:
        raise ValueError("LinkedIn URL cannot be empty.")

    logger.info("Regenerating outreach message for LinkedIn URL: %s", linkedin_url)
    client = LiteLLMClient()

    response = client.regenerate_response(
        linkedin_url=linkedin_url,
        user_note=user_note,
        message_personalization=message_personalization,
    )
    return {
        "success": True,
        "status_code": 200,
        "result": response,
    }
