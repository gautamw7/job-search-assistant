import time
import requests
from backend.utils.logger import get_logger
from backend.database.repository.provider_config import get_provider_api_key
from backend.database.sql_connection import create_connection

logger = get_logger(__name__)


def check_brightdata_api() -> dict:
    """
    Functionality: Check the health of the Bright Data API by triggering a dataset and checking its progress.
    Output: a dictionary containing the status, status code, response time, and any error messages.
    Note: As there is no health endpoint for Bright Data, this function triggers a dataset and
        checks its progress to determine the API's health.
    """
    api_key = get_provider_api_key(
        provider_name="BRIGHTDATA", credential_name="BRIGHTDATA_API_KEY"
    )
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    data = {
        "input": [{"url": "https://www.linkedin.com/in/gautamw7/"}],
        "limit_per_input": None,
    }

    trigger_url = (
        "https://api.brightdata.com/datasets/v3/trigger"
        "?dataset_id=gd_l1viktl72bvl7bjuj0"
        "&format=json"
    )

    start = time.perf_counter()

    try:
        response = requests.post(
            trigger_url,
            headers=headers,
            json=data,
            timeout=10,
        )

        response_time_ms = (time.perf_counter() - start) * 1000

        if response.status_code != 200:
            return {
                "status": "unhealthy",
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "error_message": response.text,
            }

        result = response.json()
        snapshot_id = result.get("snapshot_id")

        if not snapshot_id:
            return {
                "status": "unhealthy",
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "error_message": "No snapshot_id returned",
            }

        progress_url = f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"

        response = requests.get(
            progress_url,
            headers=headers,
            timeout=10,
        )

        result = response.json()

        logger.info("Bright Data API response: %s", result)

        status = result.get("status")

        if status == "ready":
            return {
                "status": "healthy",
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "snapshot_id": snapshot_id,
                "error_message": None,
            }

        if status == "failed":
            return {
                "status": "unhealthy",
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "snapshot_id": snapshot_id,
                "error_message": result,
            }

        return {
            "status": status,
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "snapshot_id": snapshot_id,
            "error_message": None,
        }
    except requests.exceptions.RequestException as e:
        response_time_ms = (time.perf_counter() - start) * 1000
        logger.error("Error checking Bright Data API: %s", e)
        return {
            "status": "unhealthy",
            "status_code": None,
            "response_time_ms": response_time_ms,
            "error_message": str(e),
        }
    except Exception as e:
        response_time_ms = (time.perf_counter() - start) * 1000
        logger.error("Unexpected error checking Bright Data API: %s", e)
        return {
            "status": "unhealthy",
            "status_code": None,
            "response_time_ms": response_time_ms,
            "error_message": str(e),
        }


def check_gemini_health() -> dict:
    """
    Functionality: Check the health of the Gemini API.
    Output: a dictionary containing the status, status code, response time, and any error messages.
    """
    try:
        api_key = get_provider_api_key(
            provider_name="GOOGLE", credential_name="GEMINI_API_KEY"
        )
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        start_time = time.perf_counter()
        response = requests.get(
            "https://api.gemini.com/v1/pubticker/btcusd",
            headers=headers,
            timeout=10,
        )
        response_time_ms = (time.perf_counter() - start_time) * 1000

        if response.status_code == 200:
            return {
                "status": "healthy",
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "error_message": None,
            }
        else:
            return {
                "status": "unhealthy",
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "error_message": response.text,
            }

    except requests.exceptions.RequestException as e:
        response_time_ms = (time.perf_counter() - start_time) * 1000
        logger.error("Error checking Gemini API: %s", e)
        return {
            "status": "unhealthy",
            "status_code": None,
            "response_time_ms": response_time_ms,
            "error_message": str(e),
        }
    except Exception as e:
        response_time_ms = (time.perf_counter() - start_time) * 1000
        logger.error("Unexpected error checking Gemini API: %s", e)
        return {
            "status": "unhealthy",
            "status_code": None,
            "response_time_ms": response_time_ms,
            "error_message": str(e),
        }


def get_latest_api_status(provider_name: str) -> dict:
    """
    Objective: Retrieve the most recent API health status for a given provider from the database.
    Input: provider_name (str) - The name of the API provider.
    Output: A dictionary containing the latest API health status, or None if no record exists.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM api_status WHERE provider_name = ? ORDER BY last_checked_at DESC LIMIT 1",
            (provider_name,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "provider_name": row[1],
                "status": row[2],
                "status_code": row[3],
                "response_time_ms": row[4],
                "error_message": row[5],
                "timestamp": row[6],
            }
        else:
            return None
    except Exception as e:
        logger.error(
            "Error retrieving latest API status for '%s': %s", provider_name, e
        )
        return None
    finally:
        conn.close()


def write_api_status_to_db(status_dict: dict):
    """
    Objective: Write the API health status for multiple providers to the database.
    Input: status_dict (dict) - A dictionary where keys are provider names and values are
        dictionaries containing the API health status information.
    Output: None. The function writes the status information to the database.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        for provider_name, status_info in status_dict.items():
            cursor.execute(
                """
                INSERT INTO api_status (provider_name, status, status_code, response_time_ms, error_message, last_checked_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    provider_name,
                    status_info.get("status"),
                    status_info.get("status_code"),
                    status_info.get("response_time_ms"),
                    status_info.get("error_message"),
                    time.time(),
                ),
            )
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        logger.info(
            "API Health status written to database successfully. at %s", current_time
        )
        conn.commit()
    except Exception as e:
        logger.error("Error writing API status to database: %s", e)
    finally:
        conn.close()


def is_status_stale(status_record: dict, max_age_minutes: int = 60) -> bool:
    """
    Objective: Determine if the API health status record is stale based on its timestamp.
    Input:
        status_record (dict): The API health status record containing a 'timestamp' key.
        max_age_minutes (int): The maximum age in minutes for the status to be considered fresh
    Output: True if the status is stale, False otherwise.
    """
    if not status_record or "timestamp" not in status_record:
        return True

    current_time = time.time()
    status_time = status_record["timestamp"]
    age_minutes = (current_time - status_time) / 60

    return age_minutes > max_age_minutes


def get_api_health() -> dict:
    """
    Objective: Check the health of all API providers and return their status.
    Output: A dictionary where keys are provider names and values are dictionaries containing the API health status information.
    """
    providers = {
        "Bright Data": check_brightdata_api,
        "Gemini": check_gemini_health,
    }

    results = {}

    for provider_name, check_function in providers.items():
        latest_status = get_latest_api_status(provider_name)

        if latest_status is None:
            results[provider_name] = check_function()
            continue

        if latest_status["status"] != "healthy":
            results[provider_name] = check_function()
            continue

        if is_status_stale(latest_status, max_age_minutes=60):
            results[provider_name] = check_function()
            continue

        results[provider_name] = latest_status

    # If new status was checked for any provider, write the results to the database
    if results:
        write_api_status_to_db(results)
    return results


if __name__ == "__main__":
    logger.info("CHECKING API HEALTH")
    api_health = get_api_health()
    for provider, status in api_health.items():
        logger.info("Provider: %s, Status: %s", provider, status)
