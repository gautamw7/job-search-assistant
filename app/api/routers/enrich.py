from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.schemas import BatchEnrichRequest
from app.core.logging import get_logger
from app.infra.linkedin import is_linkedin_profile_url, normalize_url
from app.services.enrich import enrich_many, get_enrich_data, hiring_contacts
from app.services.enrich.store import load_all_profiles

logger = get_logger(__name__)

router = APIRouter(
    prefix="/enrich",
    tags=["enrich"],
    responses={404: {"description": "Not found"}},
)

# NOTE: Batch endpoint skipped for now — enrich needs more modular rework
# across fetch/processor/storage. Single-profile endpoints only.


class CardInfo(BaseModel):
    id: str | None = None
    name: str | None = None
    url: str | None = None
    position: str | None = None
    current_company_name: str | None = None
    location: str | None = None
    followers: int | None = None
    connections: int | None = None


class ActivityInfo(BaseModel):
    hiring: list[dict] = []
    dropped: list[dict] = []


class DiscoveryInfo(BaseModel):
    people_also_viewed: list[dict] = []


class EnrichedProfile(BaseModel):
    card_info: dict
    content: dict
    activity: ActivityInfo
    discovery: DiscoveryInfo
    dropped_fields: dict = {}


def _load_enriched_store() -> dict:
    return load_all_profiles()


def load_enriched_profile(linkedin_url: str) -> dict:
    store = _load_enriched_store()
    data = store.get(linkedin_url) or store.get(normalize_url(linkedin_url))
    if not data:
        logger.info("enrich profile not found url=%s", linkedin_url)
        raise HTTPException(status_code=404, detail="Profile not found")
    # Back-compat: old string entries vs new dict
    if isinstance(data, str):
        logger.warning("legacy string enrich data url=%s", linkedin_url)
        raise HTTPException(
            status_code=404, detail="Profile not in new format — re-enrich required"
        )
    return data


@router.get("/cards")
def get_all_cards():
    """Card info for every enriched profile, in one call (used by the history UI)."""
    store = load_all_profiles()
    return {
        url: entry["card_info"]
        for url, entry in store.items()
        if isinstance(entry, dict) and isinstance(entry.get("card_info"), dict)
    }


class RefreshRequest(BaseModel):
    linkedin_url: str


@router.post("/refresh")
def refresh_profile(req: RefreshRequest):
    """Re-scrape a profile, replacing the cached copy."""
    if not is_linkedin_profile_url(req.linkedin_url):
        raise HTTPException(status_code=422, detail="Invalid LinkedIn profile URL")
    url = normalize_url(req.linkedin_url)
    logger.info("enrich refresh request url=%s", url)
    try:
        get_enrich_data(url, force_refresh=True)
    except Exception as e:
        logger.exception("enrich refresh failed url=%s", url)
        raise HTTPException(status_code=502, detail=str(e)) from e
    return load_enriched_profile(url)


@router.post("/batch")
def batch_enrich(req: BatchEnrichRequest):
    """Scrape several profiles in ONE BrightData request and report hiring posts."""
    urls = [u for u in req.linkedin_urls if is_linkedin_profile_url(u)]
    if not urls:
        raise HTTPException(status_code=422, detail="No valid LinkedIn profile URLs.")
    try:
        return enrich_many(urls, force_refresh=req.refresh)
    except Exception as e:
        logger.exception("batch enrich failed")
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/{linkedin_url:path}/hiring-contacts")
def get_hiring_contacts(linkedin_url: str):
    """'People also viewed' with free hiring hints and known hiring-post counts."""
    try:
        return hiring_contacts(normalize_url(linkedin_url))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=500, detail="Failed to load enrich store"
        ) from e


@router.get("/{linkedin_url:path}/card")
def get_card_info(linkedin_url: str):
    logger.info("enrich card request url=%s", linkedin_url)
    data = load_enriched_profile(linkedin_url)
    if "card_info" not in data:
        logger.warning("enrich card not found url=%s", linkedin_url)
        raise HTTPException(status_code=404, detail="Card info not found")
    logger.debug("enrich card hit url=%s", linkedin_url)
    return data["card_info"]


@router.get("/{linkedin_url:path}/content")
def get_content_info(linkedin_url: str):
    logger.info("enrich content request url=%s", linkedin_url)
    data = load_enriched_profile(linkedin_url)
    if "content" not in data:
        logger.warning("enrich content not found url=%s", linkedin_url)
        raise HTTPException(status_code=404, detail="Content info not found")
    logger.debug("enrich content hit url=%s", linkedin_url)
    return data["content"]


@router.get("/{linkedin_url:path}/activity")
def get_activity_info(linkedin_url: str):
    logger.info("enrich activity request url=%s", linkedin_url)
    data = load_enriched_profile(linkedin_url)
    if "activity" not in data:
        logger.warning("enrich activity not found url=%s", linkedin_url)
        raise HTTPException(status_code=404, detail="Activity info not found")
    logger.debug(
        "enrich activity hit url=%s hiring=%s dropped=%s",
        linkedin_url,
        len(data["activity"].get("hiring", [])),
        len(data["activity"].get("dropped", [])),
    )
    return data["activity"]


@router.get("/{linkedin_url:path}/discovery")
def get_discovery_info(linkedin_url: str):
    logger.info("enrich discovery request url=%s", linkedin_url)
    data = load_enriched_profile(linkedin_url)
    if "discovery" not in data:
        logger.warning("enrich discovery not found url=%s", linkedin_url)
        raise HTTPException(status_code=404, detail="Discovery info not found")
    logger.debug(
        "enrich discovery hit url=%s people=%s",
        linkedin_url,
        len(data["discovery"].get("people_also_viewed", [])),
    )
    return data["discovery"]


@router.get("/{linkedin_url:path}")
def get_enriched_profile(linkedin_url: str):
    logger.info("enrich full profile request url=%s", linkedin_url)
    return load_enriched_profile(linkedin_url)
