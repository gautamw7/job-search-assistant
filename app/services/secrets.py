"""Central secrets manager — keyring + file + env, with os.environ sync.

Provides get_brightdata_key() / get_gemini_key() for services that previously
used os.getenv directly, so UI-saved keys are visible without restart.
"""

import json
import os

import keyring

from app.core.logging import get_logger
from app.core.settings import SECRETS_FILE

logger = get_logger(__name__)

_SERVICE_ENV = {"brightdata": "BRIGHTDATA_API_KEY", "gemini": "GEMINI_API_KEY"}


def _mask_key(key: str) -> str:
    from app.infra.text import mask_key as _utils_mask

    return _utils_mask(key)


def _get_local_secret(service: str) -> str | None:
    try:
        if SECRETS_FILE.exists():
            with open(SECRETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(service)
    except Exception as e:
        logger.warning("failed to read local secret service=%s err=%s", service, e)
    return None


def _set_local_secret(service: str, api_key: str):
    try:
        data = {}
        if SECRETS_FILE.exists():
            with open(SECRETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data[service] = api_key
        SECRETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SECRETS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        # Harden file permission when possible
        try:
            SECRETS_FILE.chmod(0o600)
        except Exception:  # noqa: S110
            pass
        logger.info("saved local secret service=%s path=%s", service, SECRETS_FILE)
    except Exception as e:
        logger.exception("failed to save local secret service=%s err=%s", service, e)


def get_secure_key(service: str) -> str | None:
    env_name = _SERVICE_ENV.get(service)
    try:
        key = keyring.get_password(f"jobsearchassistant_{service}", "api_key")
        if key:
            logger.debug("retrieved key from keyring service=%s", service)
            if env_name:
                os.environ[env_name] = key
            return key
    except Exception as e:
        logger.warning("keyring get failed service=%s err=%s", service, e)
    key = _get_local_secret(service)
    if key:
        logger.debug("retrieved key from local secret service=%s", service)
        if env_name:
            os.environ[env_name] = key
        return key
    if env_name and os.getenv(env_name):
        logger.debug("retrieved key from env service=%s", service)
        return os.getenv(env_name)
    logger.debug("no stored key found service=%s", service)
    return None


def _remove_local_secret(service: str) -> None:
    """Drop a stale plaintext copy once the key lives in the OS keyring."""
    try:
        if not SECRETS_FILE.exists():
            return
        with open(SECRETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if service in data:
            del data[service]
            if data:
                with open(SECRETS_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            else:
                SECRETS_FILE.unlink()
            logger.info("removed plaintext copy service=%s", service)
    except Exception as e:
        logger.warning("failed to remove local secret service=%s err=%s", service, e)


def set_secure_key(service: str, api_key: str):
    """Store in the OS keyring; fall back to a 0600 file only if that fails."""
    env_name = _SERVICE_ENV.get(service)
    try:
        keyring.set_password(f"jobsearchassistant_{service}", "api_key", api_key)
        logger.info("saved key to keyring service=%s", service)
        _remove_local_secret(service)
    except Exception as e:
        logger.warning(
            "keyring set failed service=%s err=%s, falling back to local storage",
            service,
            e,
        )
        _set_local_secret(service, api_key)
    if env_name:
        os.environ[env_name] = api_key
        logger.info("synced key to os.environ service=%s env=%s", service, env_name)


def get_brightdata_key() -> str | None:
    return get_secure_key("brightdata")


def get_gemini_key() -> str | None:
    return get_secure_key("gemini")


def mask_key(key: str) -> str:
    return _mask_key(key)


def get_adzuna_credentials() -> tuple[str, str] | None:
    app_id, app_key = get_secure_key("adzuna_app_id"), get_secure_key("adzuna_app_key")
    return (app_id, app_key) if app_id and app_key else None


def get_apify_token() -> str | None:
    return get_secure_key("apify")
