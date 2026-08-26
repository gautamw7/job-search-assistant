import time
import requests

from backend.database.repository.provider_config import get_provider_api_key
from backend.utils.helper import url_normalize
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class BrightDataClient:
    """
    Client for communicating with the Bright Data API.

    Responsibilities:
        - Load and store the Bright Data API credentials.
        - Build Bright Data request payloads.
        - Trigger Bright Data datasets.
        - Check dataset progress.
        - Provide a reusable health check.
    """

    def __init__(self):
        self._api_key = get_provider_api_key(
            provider_name="brightdata",
            credential_name="BRIGHTDATA_API_KEY",
        )

        if not self._api_key:
            logger.error("Bright Data API key is not configured.")
            raise ValueError("Bright Data API key is not configured.")

        self._trigger_url = (
            "https://api.brightdata.com/datasets/v3/trigger"
            "?dataset_id=gd_l1viktl72bvl7bjuj0"
            "&format=json"
        )

        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        self._health_check_url = "https://api.brightdata.com/network_status/all"

    def check_health(self) -> dict:
        """
        Check Bright Data availability.
        Returns health status dict or raises an error.
        """
        try:
            response = requests.get(
                self._health_check_url, headers=self._headers, timeout=10
            )
            is_healthy = "healthy" if response.status_code == 200 else "unhealthy"

            return {
                "status": is_healthy,
                "status_code": response.status_code,
                "error_message": response.text if response.status_code != 200 else None,
            }
        except requests.exceptions.RequestException as exc:
            logger.error("Error checking Bright Data health: %s", exc)
            return {
                "status": "unhealthy",
                "status_code": None,
                "error_message": "Error checking Bright Data health. Exception: "
                + str(exc),
            }

    def create_payload(self, linkedin_urls: list[str]) -> list[dict]:
        return [{"url": url_normalize(url)} for url in linkedin_urls]

    def trigger_dataset(self, linkedin_urls: list[str]) -> dict:
        """
        Trigger a Bright Data dataset for the supplied LinkedIn URLs.
        Returns the JSON result dictionary on success or raises an exception.
        """
        payload = self.create_payload(linkedin_urls)
        start_time = time.perf_counter()

        try:
            response = requests.post(
                self._trigger_url,
                headers=self._headers,
                json=payload,
                timeout=10,
            )

            response_time_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code != 200:
                raise RuntimeError(
                    f"Bright Data error (Status {response.status_code}): {response.text}"
                )

            result = response.json()
            snapshot_id = result.get("snapshot_id")

            if not snapshot_id:
                raise RuntimeError(
                    f"Bright Data error: No snapshot_id returned in response: {result}"
                )

            return {
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "snapshot_id": snapshot_id,
                "result": result,
            }

        except requests.exceptions.RequestException as exc:
            response_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error("Error triggering Bright Data dataset: %s", exc)
            raise RuntimeError(f"Error triggering Bright Data dataset: {exc}")

    def get_progress(self, snapshot_id: str) -> dict:
        """
        Get the current progress of a Bright Data dataset.
        """
        progress_url = f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"

        start_time = time.perf_counter()

        try:
            response = requests.get(progress_url, headers=self._headers, timeout=10)
            response_time_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code != 200:
                raise RuntimeError(
                    f"Bright Data progress error (Status {response.status_code}): {response.text}"
                )

            result = response.json()
            logger.info("Bright Data progress response: %s", result)

            return {
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "snapshot_id": snapshot_id,
                "status": result.get("status"),
                "result": result,
            }

        except requests.exceptions.RequestException as exc:
            response_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error("Error getting Bright Data progress: %s", exc)
            raise RuntimeError(f"Error getting Bright Data progress: {exc}")
