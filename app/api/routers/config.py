import requests
from fastapi import APIRouter, HTTPException

from app.api.schemas import APIKeyRequest
from app.services.logger import get_logger
from app.services.secrets import (
    get_secure_key as _secrets_get,
)
from app.services.secrets import (
    mask_key as _mask_key,
)
from app.services.secrets import (
    set_secure_key as _secrets_set,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/config",
    tags=["config"],
    responses={404: {"description": "Not found"}},
)


def _get_local_secret(service: str) -> str | None:
    """Backward compat shim — keep symbol for tests that patch it."""
    from app.services.secrets import _get_local_secret as _impl

    return _impl(service)


def _set_local_secret(service: str, api_key: str):
    from app.services.secrets import _set_local_secret as _impl

    _impl(service, api_key)


def get_secure_key(service: str) -> str | None:
    return _secrets_get(service)


def set_secure_key(service: str, api_key: str):
    _secrets_set(service, api_key)


def test_brightdata_connection(api_key: str):
    if not api_key or len(api_key) < 5:
        logger.warning(
            "brightdata key format invalid len=%s", len(api_key) if api_key else 0
        )
        raise HTTPException(status_code=400, detail="Invalid API key format.")
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        logger.info("testing brightdata connection")
        response = requests.get(
            "https://api.brightdata.com/network_status/all", headers=headers, timeout=8
        )
        if response.status_code in [401, 403]:
            logger.warning("brightdata auth failed status=%s", response.status_code)
            raise HTTPException(
                status_code=400, detail="Invalid BrightData API key (Unauthorized)."
            )
        logger.info(
            "brightdata connection test succeeded status=%s", response.status_code
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("brightdata connection test network error: %s", e)


def test_gemini_connection(api_key: str):
    if not api_key or len(api_key) < 5:
        logger.warning(
            "gemini key format invalid len=%s", len(api_key) if api_key else 0
        )
        raise HTTPException(status_code=400, detail="Invalid API key format.")
    try:
        logger.info("testing gemini connection")
        response = requests.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
            timeout=8,
        )
        if response.status_code in [400, 401, 403]:
            logger.warning("gemini auth failed status=%s", response.status_code)
            raise HTTPException(
                status_code=400,
                detail="Invalid Gemini API key (Unauthorized/Forbidden).",
            )
        logger.info("gemini connection test succeeded status=%s", response.status_code)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("gemini connection test network error: %s", e)


@router.post("/brightdata")
def store_brightdata_credentials(req: APIKeyRequest):
    api_key = req.api_key.strip()
    if not api_key:
        logger.warning("brightdata store failed: empty key")
        raise HTTPException(status_code=400, detail="API key is required.")
    logger.info("storing brightdata credentials")
    test_brightdata_connection(api_key)
    set_secure_key("brightdata", api_key)
    logger.info("brightdata credentials stored successfully")
    return {"message": "BrightData credentials stored successfully."}


@router.post("/gemini")
def store_gemini_credentials(req: APIKeyRequest):
    api_key = req.api_key.strip()
    if not api_key:
        logger.warning("gemini store failed: empty key")
        raise HTTPException(status_code=400, detail="API key is required.")
    logger.info("storing gemini credentials")
    test_gemini_connection(api_key)
    set_secure_key("gemini", api_key)
    logger.info("gemini credentials stored successfully")
    return {"message": "Gemini credentials stored successfully."}


@router.get("/brightdata")
def get_brightdata_credentials():
    api_key = get_secure_key("brightdata")
    if not api_key:
        logger.info("brightdata credentials not found")
        raise HTTPException(status_code=404, detail="Credentials not found.")
    logger.debug(
        "brightdata credentials retrieved service=brightdata masked=%s",
        _mask_key(api_key),
    )
    # Do not return full key; return masked existence check
    return {"masked": _mask_key(api_key), "exists": True, "api_key": _mask_key(api_key)}


@router.post("/brightdata/test")
def test_stored_brightdata_credentials():
    api_key = get_secure_key("brightdata")
    if not api_key:
        logger.warning("brightdata test failed: no stored credentials")
        raise HTTPException(status_code=404, detail="Credentials not found.")
    logger.info("testing stored brightdata credentials")
    test_brightdata_connection(api_key)
    logger.info("stored brightdata credentials valid")
    return {"message": "BrightData API key is valid and working."}


@router.get("/gemini")
def get_gemini_credentials():
    api_key = get_secure_key("gemini")
    if not api_key:
        logger.info("gemini credentials not found")
        raise HTTPException(status_code=404, detail="Credentials not found.")
    logger.debug(
        "gemini credentials retrieved service=gemini masked=%s", _mask_key(api_key)
    )
    return {"masked": _mask_key(api_key), "exists": True, "api_key": _mask_key(api_key)}


@router.post("/gemini/test")
def test_stored_gemini_credentials():
    api_key = get_secure_key("gemini")
    if not api_key:
        logger.warning("gemini test failed: no stored credentials")
        raise HTTPException(status_code=404, detail="Credentials not found.")
    logger.info("testing stored gemini credentials")
    test_gemini_connection(api_key)
    logger.info("stored gemini credentials valid")
    return {"message": "Gemini API key is valid and working."}
