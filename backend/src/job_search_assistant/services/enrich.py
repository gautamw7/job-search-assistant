import json
import re
import time
from pathlib import Path

import requests

from job_search_assistant.services.logger import get_logger
from job_search_assistant.services.secrets import get_brightdata_key

logger = get_logger(__name__)

CARD_FIELDS = {
    "id",
    "name",
    "url",
    "position",
    "current_company_name",
    "location",
    "followers",
    "connections",
}

CONTENT_FIELDS = {
    "about",
    "current_company_name",
    "country_code",
    "educations_details",
    "education",
    "languages",
    "bio_links",
    "experience",
    "certifications",
}

HIRING_PATTERNS = [
    r"\bhiring\b",
    r"#hiring\b",
    r"\bwe(?:'re| are) hiring\b",
    r"\bjob opening\b",
    r"\bjob openings\b",
    r"\bjob opportunity\b",
    r"\bjob opportunities\b",
    r"\bcareer opportunity\b",
    r"\bcareer opportunities\b",
    r"\bopen position\b",
    r"\bopen positions\b",
    r"\bjob alert\b",
    r"\bwe are looking for\b",
    r"\bis looking for\b",
    r"\blooking for\b",
    r"\bjoin our team\b",
    r"\bjoin the team\b",
    r"\bapply now\b",
    r"\bapplications? (?:are|is) (?:open|invited)\b",
    r"\b(?:send|share) (?:your|updated) (?:cv|resume)\b",
    r"\brecruit(?:ing|ment)\b",
    r"\bvacanc(?:y|ies)\b",
    r"\bWir suchen\b",
]

HIRING_REGEX = re.compile("|".join(HIRING_PATTERNS), flags=re.IGNORECASE)


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
    API_KEY = get_brightdata_key()

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    input_data = generate_input_json(linkedin_urls)

    # Trigger the async collection
    logger.info(
        "brightdata trigger start dataset_id=%s urls=%s", DATASET_ID, linkedin_urls
    )
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
        logger.error(
            "brightdata trigger failed status=%s body=%.500s",
            trigger_response.status_code,
            trigger_response.text,
        )
        raise ValueError(f"Bright Data trigger failed: {trigger_response.text}")

    snapshot_id = trigger_response.json()["snapshot_id"]
    logger.info("brightdata snapshot_id=%s", snapshot_id)

    # Poll progress until ready
    while True:
        progress_response = requests.get(
            f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
            headers={"Authorization": f"Bearer {API_KEY}"},
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

    # Download results
    logger.info("brightdata downloading results snapshot_id=%s", snapshot_id)
    results_response = requests.get(
        f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
        params={"format": "json"},
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    results_response.raise_for_status()

    logger.info(
        "brightdata results received count=%s snapshot_id=%s",
        len(results_response.json())
        if isinstance(results_response.json(), list)
        else 0,
        snapshot_id,
    )
    return results_response.json()


def _extract_card_info(user_data: dict) -> dict:
    """Extract card fields for UI card display."""
    return {k: user_data[k] for k in CARD_FIELDS if k in user_data}


def _extract_content(user_data: dict) -> dict:
    """Extract content fields for generation/storage."""
    return {k: user_data[k] for k in CONTENT_FIELDS if k in user_data}


def _classify_activity(activity: list | None) -> dict:
    """Split activity into hiring vs dropped using HIRING_REGEX."""
    hiring: list[dict] = []
    dropped: list[dict] = []
    if not isinstance(activity, list):
        return {"hiring": hiring, "dropped": dropped}
    for post in activity:
        if not isinstance(post, dict):
            dropped.append(post)
            continue
        title = post.get("title")
        if title and HIRING_REGEX.search(title):
            hiring.append(post)
        else:
            dropped.append(post)
    return {"hiring": hiring, "dropped": dropped}


def _extract_discovery(user_data: dict) -> dict:
    """Extract people_also_viewed for discovery. Keeps all 20."""
    people = user_data.get("people_also_viewed")
    if isinstance(people, list):
        return {"people_also_viewed": people}
    return {"people_also_viewed": []}


def _extract_dropped_fields(user_data: dict) -> dict:
    """Collect keys not in any bucket for audit."""
    return {
        k: v
        for k, v in user_data.items()
        if k not in CARD_FIELDS
        and k not in CONTENT_FIELDS
        and k not in {"activity", "people_also_viewed"}
    }


def process_enrich_data(user_data: dict) -> dict:
    """
    Process an enriched LinkedIn profile in a single pass (modular).

    Delegates to _extract_* helpers so batch can reuse them without rework.
    Keeps experience: None and all 20 people_also_viewed as requested.
    """
    card_info = _extract_card_info(user_data)
    content = _extract_content(user_data)
    activity = _classify_activity(user_data.get("activity"))
    discovery = _extract_discovery(user_data)
    dropped_fields = _extract_dropped_fields(user_data)

    return {
        "card_info": card_info,
        "content": content,
        "activity": activity,
        "discovery": discovery,
        "dropped_fields": dropped_fields,
    }


def content_to_markdown(content: dict) -> str:
    """
    Convert content dict to markdown string.
    Format: ## key and then ### content as requested.
    Handles str, None, list[dict], dict.
    """
    md_parts: list[str] = []
    for key, value in content.items():
        md_parts.append(f"## {key}")
        if value is None:
            md_parts.append("None")
        elif isinstance(value, list):
            if not value:
                md_parts.append("None")
            else:
                for item in value:
                    if isinstance(item, dict):
                        for k2, v2 in item.items():
                            md_parts.append(f"### {k2}: {v2}")
                        md_parts.append("")
                    else:
                        md_parts.append(f"- {item}")
        elif isinstance(value, dict):
            for k2, v2 in value.items():
                md_parts.append(f"### {k2}: {v2}")
        else:
            # str or other
            md_parts.append(f"{value}")
        md_parts.append("")  # blank line between sections
    return "\n".join(md_parts).strip()


def save_enrich_data(enrich_data: dict, output_path: str | None = None) -> None:
    """
    Save the enrichment data dictionary to a JSON file.
    Appends content/activity/discovery instead of replacing.

    Args:
        enrich_data (dict): Dictionary mapping LinkedIn URL to enrichment data.
        output_path (str | None): File destination path. Defaults to backend/data/enrich_data.json via paths.
    """
    from job_search_assistant.services.paths import DATA_DIR

    # Resolve default to backend/data when not provided (fixes cwd vs backend mismatch)
    if output_path is None or output_path == "data/enrich_data.json":
        path = DATA_DIR / "enrich_data.json"
    else:
        path = Path(output_path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    # Merge with existing file if present
    existing = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning("failed to load existing enrich data path=%s", path)
            existing = {}

    # Deep merge per URL: append lists instead of replacing content
    for url, new_data in enrich_data.items():
        if (
            url not in existing
            or not isinstance(existing[url], dict)
            or isinstance(existing[url], str)
        ):
            # First time or legacy string -> replace
            existing[url] = new_data
            continue

        old = existing[url]
        # Merge card_info (replace with new, keep missing old fields)
        old_card = old.get("card_info", {})
        new_card = new_data.get("card_info", {})
        old["card_info"] = {**old_card, **new_card}

        # Merge content: extend lists, replace scalars
        old_content = old.get("content", {})
        new_content = new_data.get("content", {})
        for k, v in new_content.items():
            if k not in old_content:
                old_content[k] = v
            elif isinstance(v, list) and isinstance(old_content[k], list):
                # Append unique items
                existing_ids = {
                    json.dumps(x, sort_keys=True)
                    for x in old_content[k]
                    if isinstance(x, dict)
                }
                for item in v:
                    key = (
                        json.dumps(item, sort_keys=True)
                        if isinstance(item, dict)
                        else str(item)
                    )
                    if key not in existing_ids:
                        old_content[k].append(item)
            elif isinstance(v, dict) and isinstance(old_content[k], dict):
                old_content[k] = {**old_content[k], **v}
            else:
                old_content[k] = v
        old["content"] = old_content

        # Merge activity hiring/dropped: append
        old_act = old.get("activity", {"hiring": [], "dropped": []})
        new_act = new_data.get("activity", {"hiring": [], "dropped": []})
        for key in ("hiring", "dropped"):
            old_list = (
                old_act.get(key, []) if isinstance(old_act.get(key), list) else []
            )
            new_list = (
                new_act.get(key, []) if isinstance(new_act.get(key), list) else []
            )
            # dedupe by json dump
            seen = {json.dumps(x, sort_keys=True) for x in old_list}
            for item in new_list:
                j = json.dumps(item, sort_keys=True)
                if j not in seen:
                    old_list.append(item)
                    seen.add(j)
            old_act[key] = old_list
        old["activity"] = old_act

        # Merge discovery people_also_viewed: append unique by profile_link
        old_disc = old.get("discovery", {"people_also_viewed": []})
        new_disc = new_data.get("discovery", {"people_also_viewed": []})
        old_people = (
            old_disc.get("people_also_viewed", [])
            if isinstance(old_disc.get("people_also_viewed"), list)
            else []
        )
        new_people = (
            new_disc.get("people_also_viewed", [])
            if isinstance(new_disc.get("people_also_viewed"), list)
            else []
        )
        seen_links = {p.get("profile_link") for p in old_people if isinstance(p, dict)}
        for p in new_people:
            if isinstance(p, dict) and p.get("profile_link") not in seen_links:
                old_people.append(p)
                seen_links.add(p.get("profile_link"))
        old_disc["people_also_viewed"] = old_people
        old["discovery"] = old_disc

        # Merge dropped_fields: update
        old_drop = old.get("dropped_fields", {})
        new_drop = new_data.get("dropped_fields", {})
        if isinstance(old_drop, dict) and isinstance(new_drop, dict):
            old_drop.update(new_drop)
            old["dropped_fields"] = old_drop

        existing[url] = old

    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4)

    logger.info(
        "enrich data saved path=%s entries=%s (appended content where exists)",
        path,
        len(enrich_data),
    )


def map_enrich_data_by_url(results: list) -> dict:
    """
    Map raw profile results from API to processed dict keyed by input URL.

    Args:
        results (list): Raw list of profile dicts from API.

    Returns:
        dict: Mapping of input_url to processed EnrichedProfile dict.
    """
    return {
        profile["input_url"]: process_enrich_data(profile)
        for profile in results
        if profile.get("input_url")
    }


def cached_enrich_data(linkedin_url: str) -> dict:
    """
    Load enrichment data from cache if available.

    Args:
        linkedin_url (str): LinkedIn profile URL to check in cache.

    Returns:
        dict: Cached enrichment data if found, else empty dict.
    """
    from job_search_assistant.services.paths import ENRICH_DATA

    path = ENRICH_DATA
    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            existing = json.load(f)
            cached = existing.get(linkedin_url, {})
            if isinstance(cached, dict) and (
                cached.get("content") or cached.get("card_info")
            ):
                return cached
            return {}
    except json.JSONDecodeError as e:
        logger.warning("failed to load cached enrich data path=%s err=%s", path, e)
        return {}


def get_enrich_data(linkedin_url: str, force_refresh: bool = False) -> str:
    """
    Fetch, process, and persist enrichment data for a single LinkedIn URL.

    Checks local cache first unless force_refresh is True.

    Args:
        linkedin_url (str): A single LinkedIn profile URL string.
        force_refresh (bool): If True, bypass cache and fetch fresh from API.

    Returns:
        str: Markdown string of card_info and content for generation.
    """
    logger.info(
        "get_enrich_data start url=%s force_refresh=%s", linkedin_url, force_refresh
    )
    cached = None if force_refresh else cached_enrich_data(linkedin_url)
    if cached:
        logger.info("cached enrich data found url=%s", linkedin_url)
        processed = cached
    else:
        results = fetch_enrich_data([linkedin_url])
        if not results:
            logger.warning("no enrichment data found url=%s", linkedin_url)
            return ""

        profile = results[0]
        processed = process_enrich_data(profile)
        save_enrich_data({linkedin_url: processed})

    content_md = content_to_markdown(processed.get("content", {}))
    card_info_md = content_to_markdown(processed.get("card_info", {}))

    content = f"# Card Info\n{card_info_md}\n\n# Content\n{content_md}".strip()

    activity_hiring = (
        processed.get("activity", {}).get("hiring", [])
        if isinstance(processed.get("activity"), dict)
        else []
    )
    activity_dropped = (
        processed.get("activity", {}).get("dropped", [])
        if isinstance(processed.get("activity"), dict)
        else []
    )
    discovery_people = (
        processed.get("discovery", {}).get("people_also_viewed", [])
        if isinstance(processed.get("discovery"), dict)
        else []
    )

    logger.info(
        "get_enrich_data done url=%s content_md_len=%s hiring=%s dropped=%s people=%s",
        linkedin_url,
        len(content),
        len(activity_hiring),
        len(activity_dropped),
        len(discovery_people),
    )

    return content
