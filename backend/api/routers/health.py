"""
Objective:
1. Provide the health check endpoint for the API.
"""

from fastapi import APIRouter
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
def health_check() -> bool:
    """
    Health check endpoint to verify the API is running.

    Returns:
        bool: True if the API is healthy, False otherwise.
    """
    return True
