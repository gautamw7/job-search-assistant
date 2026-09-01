import json
import time
import requests
import os
from pathlib import Path


def generate_input_json(linkedin_urls: list) -> list[dict]:
    """
    Generate JSON payload structure for Bright Data trigger API.

    Args:
        linkedin_urls (list): List of LinkedIn URL strings.

    Returns:
        list[dict]: Formatted input payload list.
    """
    return [{"url": url} for url in linkedin_urls]


def fetch_enrich_data(linkedin_urls: list) -> list:
    """
    Fetch raw profile enrichment data for the provided LinkedIn URLs via BrightData API.

    Args:
        linkedin_urls (list): List of LinkedIn profile URLs to enrich.

    Returns:
        list: Raw JSON result list returned by BrightData API.
    """
    DATASET_ID = "gd_l1viktl72bvl7bjuj0"
    API_KEY = os.getenv("BRIGHTDATA_API_KEY")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    input_data = generate_input_json(linkedin_urls)

    # Trigger the async collection
    trigger_response = requests.post(
        "https://api.brightdata.com/datasets/v3/trigger",
        params={
            "dataset_id": DATASET_ID,
            "format": "json",
        },
        headers=headers,
        json=input_data,
    )
    if not trigger_response.ok:
        print("Bright Data status:", trigger_response.status_code)
        print("Bright Data response:", trigger_response.text)
        raise RuntimeError(
            f"Bright Data trigger failed: {trigger_response.text}"
        )

    snapshot_id = trigger_response.json()["snapshot_id"]
    print("Snapshot ID:", snapshot_id)

    # Poll progress until ready
    while True:
        progress_response = requests.get(
            f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
        progress_response.raise_for_status()

        status = progress_response.json().get("status")
        print("Status:", status)

        if status == "ready":
            break
        if status == "failed":
            raise Exception(f"Collection failed: {progress_response.text}")

        time.sleep(10)

    # Download results
    results_response = requests.get(
        f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
        params={"format": "json"},
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    results_response.raise_for_status()

    return results_response.json()


def process_enrich_data(user_data, indent=0, enrich_string: str = "") -> str:
    """
    Recursively format profile dictionary into a human-readable structured string.

    Args:
        user_data: Profile dict, list, or primitive value.
        indent (int): Current indentation level.
        enrich_string (str): Accumulated formatted string.

    Returns:
        str: Indented tree text representation of the profile data.
    """
    if not isinstance(user_data, dict):
        return enrich_string + (" " * indent + str(user_data)) + "\n"

    for key, value in user_data.items():
        enrich_string += (" " * indent + str(key) + ":") + "\n"

        if isinstance(value, dict):
            enrich_string = process_enrich_data(value, indent + 4, enrich_string)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    enrich_string = process_enrich_data(item, indent + 4, enrich_string)
                else:
                    enrich_string += (" " * (indent + 4) + str(item)) + "\n"
        else:
            enrich_string += (" " * (indent + 4) + str(value)) + "\n"

    return enrich_string


def save_enrich_data(enrich_data: dict, output_path: str = "data/enrich_data.json") -> None:
    """
    Save the enrichment data dictionary to a JSON file.

    Args:
        enrich_data (dict): Dictionary mapping LinkedIn URL to enrichment data.
        output_path (str): File destination path.
    """
    path = Path(output_path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    # Merge with existing file if present
    existing = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    existing.update(enrich_data)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4)

    print(f"Enrich data saved to {output_path}")


def map_enrich_data_by_url(results: list) -> dict:
    """
    Map raw profile results from API to formatted enrichment strings keyed by input URL.

    Args:
        results (list): Raw list of profile dicts from API.

    Returns:
        dict: Mapping of input_url to formatted enrichment string.
    """
    return {
        profile["input_url"]: process_enrich_data(profile, indent=0, enrich_string="")
        for profile in results
        if profile.get("input_url")
    }


def get_enrich_data(linkedin_url: str) -> str:
    """
    Fetch, process, and persist enrichment data for a single LinkedIn URL.

    Args:
        linkedin_url (str): A single LinkedIn profile URL string.

    Returns:
        str: Formatted enrichment text string for the profile.
    """
    results = fetch_enrich_data([linkedin_url])
    if not results:
        print(f"Warning: No enrichment data found for {linkedin_url}")
        return ""

    profile = results[0]
    enrich_str = process_enrich_data(profile, indent=0, enrich_string="")

    save_enrich_data({linkedin_url: enrich_str})

    return enrich_str
