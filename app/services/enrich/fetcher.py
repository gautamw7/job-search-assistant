"""Internal: BrightData fetch — trigger, poll, download."""

import time

import requests

from app.services.logger import get_logger
from app.services.secrets import get_brightdata_key

logger = get_logger(__name__)


def generate_input_json(linkedin_urls: list) -> list[dict]:
    return [{"url": url} for url in linkedin_urls]


def fetch_enrich_data(linkedin_urls: list) -> list:
    dataset_id = "gd_l1viktl72bvl7bjuj0"
    api_key = get_brightdata_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    input_data = generate_input_json(linkedin_urls)

    logger.info("brightdata trigger start dataset_id=%s urls=%s", dataset_id, linkedin_urls)
    trigger_response = requests.post(
        "https://api.brightdata.com/datasets/v3/trigger",
        params={"dataset_id": dataset_id, "format": "json"},
        headers=headers,
        json=input_data,
    )
    if not trigger_response.ok:
        logger.error(
            "brightdata trigger failed status=%s body=%.500s",
            trigger_response.status_code,
            trigger_response.text,
        )
        raise ValueError(f"Bright Data trigger failed: {trigger_response.text}")

    snapshot_id = trigger_response.json()["snapshot_id"]
    logger.info("brightdata snapshot_id=%s", snapshot_id)

    while True:
        progress_response = requests.get(
            f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        progress_response.raise_for_status()
        status = progress_response.json().get("status")
        logger.info("brightdata poll status=%s snapshot_id=%s", status, snapshot_id)
        if status == "ready":
            break
        if status == "failed":
            logger.error(
                "brightdata collection failed snapshot_id=%s body=%.500s",
                snapshot_id,
                progress_response.text,
            )
            raise ValueError(f"Collection failed: {progress_response.text}")
        time.sleep(10)

    logger.info("brightdata downloading results snapshot_id=%s", snapshot_id)
    results_response = requests.get(
        f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
        params={"format": "json"},
        headers={"Authorization": f"Bearer {api_key}"},
    )
    results_response.raise_for_status()
    logger.info(
        "brightdata results received count=%s snapshot_id=%s",
        len(results_response.json()) if isinstance(results_response.json(), list) else 0,
        snapshot_id,
    )
    return results_response.json()
