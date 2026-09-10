from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.enrich.store import load_enrichment_store
from app.services.logger import get_logger
from app.services.paths import DATA_DIR

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
    file_path = DATA_DIR / "enrich_data.json"
    if not file_path.exists():
        logger.warning("enrich store not found path=%s", file_path)
        raise HTTPException(status_code=404, detail="Enrich store not found")
    try:
        return load_enrichment_store(file_path)
    except ValueError as e:
        logger.exception("failed to load enrich store err=%s", e)
        raise HTTPException(status_code=500, detail="Failed to load enrich store") from e


def load_enriched_profile(linkedin_url: str) -> dict:
    data = _load_enriched_store().get(linkedin_url)
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
