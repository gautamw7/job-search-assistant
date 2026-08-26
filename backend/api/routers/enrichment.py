from fastapi import APIRouter
from backend.utils.logger import get_logger
from backend.clients.brightdata import BrightDataClient

logger = get_logger(__name__)

router = APIRouter(prefix="/enrichment", tags=["Enrichment"])


@router.post("/")
def enrich_profile(linkedlin_url: str) -> dict:
    """
    Enrich a LinkedIn profile based on the provided URL.
    """
    if not linkedlin_url:
        raise ValueError("LinkedIn URL cannot be empty.")

    brightdata_client = BrightDataClient()
    result = brightdata_client.trigger_dataset([linkedlin_url])

    return {
        "success": True,
        "status_code": 200,
        "enriched_data": result,
    }
