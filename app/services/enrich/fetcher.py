"""Internal: BrightData fetch — trigger, poll, download (with timeouts + retries)."""

import time

import requests

from app.core.logging import get_logger
from app.services import usage
from app.services.secrets import get_brightdata_key

logger = get_logger(__name__)

DATASET_ID = "gd_l1viktl72bvl7bjuj0"
API_BASE = "https://api.brightdata.com/datasets/v3"
REQUEST_TIMEOUT = (10, 60)  # (connect, read) seconds
POLL_INTERVAL_S = 5
MAX_WAIT_S = 600
MAX_ATTEMPTS = 3
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class BrightDataError(RuntimeError):
    """Raised when BrightData cannot return a profile."""


def generate_input_json(linkedin_urls: list) -> list[dict]:
    return [{"url": url} for url in linkedin_urls]


def _request(method: str, url: str, **kwargs) -> requests.Response:
    """HTTP call with timeout and bounded retry/backoff on transient failures."""
    last_exc: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
            if resp.status_code in _RETRYABLE_STATUS and attempt < MAX_ATTEMPTS:
                logger.warning(
                    "brightdata transient status=%s url=%s attempt=%s",
                    resp.status_code,
                    url,
                    attempt,
                )
            else:
                return resp
        except (requests.ConnectionError, requests.Timeout) as e:
            last_exc = e
            logger.warning(
                "brightdata network error url=%s attempt=%s err=%s", url, attempt, e
            )
        time.sleep(2 ** (attempt - 1))
    raise BrightDataError(f"BrightData unreachable: {last_exc}")


def fetch_enrich_data(linkedin_urls: list) -> list:
    api_key = get_brightdata_key()
    if not api_key:
        raise BrightDataError(
            "BrightData API key is not configured. Add it in Settings."
        )
    usage.check_budget(profiles=len(linkedin_urls))
    auth = {"Authorization": f"Bearer {api_key}"}

    logger.info(
        "brightdata trigger start dataset_id=%s urls=%s", DATASET_ID, linkedin_urls
    )
    trigger = _request(
        "POST",
        f"{API_BASE}/trigger",
        params={"dataset_id": DATASET_ID, "format": "json"},
        headers={**auth, "Content-Type": "application/json"},
        json=generate_input_json(linkedin_urls),
    )
    if not trigger.ok:
        logger.error(
            "brightdata trigger failed status=%s body=%.500s",
            trigger.status_code,
            trigger.text,
        )
        raise BrightDataError(f"Bright Data trigger failed: {trigger.text[:300]}")

    snapshot_id = trigger.json().get("snapshot_id")
    if not snapshot_id:
        raise BrightDataError("Bright Data did not return a snapshot id.")
    logger.info("brightdata snapshot_id=%s", snapshot_id)

    deadline = time.monotonic() + MAX_WAIT_S
    while True:
        progress = _request("GET", f"{API_BASE}/progress/{snapshot_id}", headers=auth)
        progress.raise_for_status()
        status = progress.json().get("status")
        logger.info("brightdata poll status=%s snapshot_id=%s", status, snapshot_id)
        if status == "ready":
            break
        if status == "failed":
            logger.error(
                "brightdata collection failed snapshot_id=%s body=%.500s",
                snapshot_id,
                progress.text,
            )
            raise BrightDataError(f"Collection failed: {progress.text[:300]}")
        if time.monotonic() >= deadline:
            raise BrightDataError(
                f"Timed out after {MAX_WAIT_S}s waiting for snapshot {snapshot_id}."
            )
        time.sleep(POLL_INTERVAL_S)

    logger.info("brightdata downloading results snapshot_id=%s", snapshot_id)
    results = _request(
        "GET",
        f"{API_BASE}/snapshot/{snapshot_id}",
        params={"format": "json"},
        headers=auth,
    )
    results.raise_for_status()
    data = results.json()
    if not isinstance(data, list):
        data = [data] if isinstance(data, dict) else []
    logger.info(
        "brightdata results received count=%s snapshot_id=%s", len(data), snapshot_id
    )
    usage.record_brightdata(len(data))
    return data
