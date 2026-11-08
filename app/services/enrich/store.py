"""Internal: enrich persistence — save/load + cache helpers."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from app.core.logging import get_logger
from app.infra.json_store import _quarantine, path_lock, save_json
from app.infra.linkedin import is_linkedin_profile_url, normalize_url
from app.services.enrich.processor import (
    activity_to_markdown,
    contact_hiring_signals,
    content_to_markdown,
    is_error_record,
    process_enrich_data,
)

logger = get_logger(__name__)

# Profiles change (job moves, new posts); older cache entries are re-scraped.
CACHE_TTL_DAYS = 30


def load_enrichment_store(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed enrich data file at {path}: {e}") from e
    except OSError as e:
        raise ValueError(f"Unable to read enrich data file at {path}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Enrich data file must contain a JSON object: {path}")  # noqa: TRY004
    return data


def save_enrich_data(enrich_data: dict, output_path: str | None = None) -> None:
    """Persist profiles keyed by URL. A newer entry replaces the older one.

    Replacing (rather than merging) means a refresh reflects the profile as it is
    now instead of accumulating stale and duplicated list items forever.
    """
    from app.core.settings import DATA_DIR

    if output_path is None or output_path == "data/enrich_data.json":
        path = DATA_DIR / "enrich_data.json"
    else:
        path = Path(output_path)

    with path_lock(path):
        try:
            existing = load_enrichment_store(path)
        except ValueError:
            # Keep the unreadable file for recovery instead of overwriting it.
            moved = _quarantine(path)
            logger.error("enrich store unreadable, quarantined to=%s", moved)
            existing = {}
        existing.update(enrich_data)
        save_json(path, existing)
    logger.info("enrich data saved path=%s entries=%s", path, len(enrich_data))


def _is_fresh(entry: dict) -> bool:
    fetched_at = entry.get("fetched_at")
    if not fetched_at:
        return True  # legacy entries without a timestamp are trusted
    try:
        age = datetime.now() - datetime.fromisoformat(fetched_at)
    except ValueError:
        return True
    return age <= timedelta(days=CACHE_TTL_DAYS)


def cached_enrich_data(linkedin_url: str) -> dict:
    from app.core.settings import ENRICH_DATA

    existing = load_enrichment_store(ENRICH_DATA)
    cached = existing.get(linkedin_url, {})
    if (
        isinstance(cached, dict)
        and (cached.get("content") or cached.get("card_info"))
        and _is_fresh(cached)
    ):
        return cached
    return {}


def _pick_record(results: list, linkedin_url: str) -> dict:
    """Choose the scraped record for this URL; never silently use an error row."""
    wanted = normalize_url(linkedin_url).casefold()
    records = [r for r in results if isinstance(r, dict)]
    good = [r for r in records if not is_error_record(r)]
    for record in good:
        if normalize_url(str(record.get("input_url", ""))).casefold() == wanted:
            return record
    if good:
        return good[0]
    reason = next((r.get("error") for r in records if r.get("error")), "no data")
    raise ValueError(f"Profile could not be scraped ({reason}).")


def get_enrich_data(linkedin_url: str, force_refresh: bool = False) -> str:
    logger.info(
        "get_enrich_data start url=%s force_refresh=%s", linkedin_url, force_refresh
    )
    cached = None if force_refresh else cached_enrich_data(linkedin_url)
    if cached:
        logger.info("cached enrich data found url=%s", linkedin_url)
        processed = cached
    else:
        # Import via package so patching services.enrich.fetch_enrich_data works in tests
        import app.services.enrich as enrich_pkg

        results = enrich_pkg.fetch_enrich_data([linkedin_url])
        if not results:
            raise ValueError("No profile data was returned for this URL.")
        processed = process_enrich_data(_pick_record(results, linkedin_url))
        processed["fetched_at"] = datetime.now().isoformat(timespec="seconds")
        enrich_pkg.save_enrich_data({linkedin_url: processed})

    content_md = content_to_markdown(processed.get("content", {}))
    card_info_md = content_to_markdown(processed.get("card_info", {}))
    sections = [f"# Card Info\n{card_info_md}", f"# Content\n{content_md}"]

    activity = processed.get("activity")
    hiring_md = activity_to_markdown(activity)
    if hiring_md:
        sections.append(f"# Recent Hiring Posts\n{hiring_md}")
    content = "\n\n".join(sections).strip()

    logger.info(
        "get_enrich_data done url=%s content_md_len=%s hiring_posts=%s",
        linkedin_url,
        len(content),
        len(activity.get("hiring", [])) if isinstance(activity, dict) else 0,
    )
    return content


MAX_BATCH = 20


def get_profile(linkedin_url: str) -> dict:
    """Processed profile dict from the store (no network), or {}."""
    from app.core.settings import ENRICH_DATA

    try:
        entry = load_enrichment_store(ENRICH_DATA).get(linkedin_url)
    except ValueError:
        return {}
    return entry if isinstance(entry, dict) else {}


def _hiring_summary(entry: dict | None) -> tuple[int | None, str | None]:
    if not isinstance(entry, dict) or not isinstance(entry.get("activity"), dict):
        return None, None
    posts = [p for p in entry["activity"].get("hiring", []) if isinstance(p, dict)]
    return len(posts), (str(posts[0].get("title", ""))[:200] if posts else None)


def hiring_contacts(linkedin_url: str) -> list[dict]:
    """'People also viewed' for a profile, with free bio signals and, for anyone
    already scraped, how many recent hiring posts they have."""
    from app.core.settings import ENRICH_DATA

    store = load_enrichment_store(ENRICH_DATA)
    profile = store.get(linkedin_url)
    if not isinstance(profile, dict):
        raise LookupError("Profile not enriched yet")  # noqa: TRY004
    people = (profile.get("discovery") or {}).get("people_also_viewed") or []

    contacts: dict[str, dict] = {}
    for person in people:
        if not isinstance(person, dict):
            continue
        link = str(person.get("profile_link") or "")
        if not is_linkedin_profile_url(link):
            continue
        url = normalize_url(link)
        if url in contacts or url == linkedin_url:
            continue
        posts, latest = _hiring_summary(store.get(url))
        contacts[url] = {
            "linkedin_url": url,
            "name": person.get("name") or "",
            "headline": person.get("about") or "",
            "location": person.get("location") or "",
            "signals": contact_hiring_signals(person.get("about")),
            "checked": posts is not None,
            "hiring_posts": posts,
            "latest_hiring_post": latest,
        }
    return sorted(
        contacts.values(),
        key=lambda c: (-(c["hiring_posts"] or 0), -len(c["signals"]), c["name"]),
    )


def enrich_many(
    linkedin_urls: list[str], force_refresh: bool = False
) -> dict[str, dict]:
    """Scrape several profiles with ONE BrightData snapshot (cheaper and faster than
    one request each). Fresh cached profiles are reused unless ``force_refresh``."""
    import app.services.enrich as enrich_pkg

    urls = list(dict.fromkeys(normalize_url(u) for u in linkedin_urls))[:MAX_BATCH]
    results: dict[str, dict] = {}
    to_fetch = []
    for url in urls:
        cached = None if force_refresh else cached_enrich_data(url)
        if cached:
            posts, latest = _hiring_summary(cached)
            results[url] = {
                "ok": True,
                "cached": True,
                "hiring_posts": posts or 0,
                "latest_hiring_post": latest,
                "error": None,
            }
        else:
            to_fetch.append(url)

    if to_fetch:
        records = enrich_pkg.fetch_enrich_data(to_fetch)
        by_url = {
            normalize_url(str(r.get("input_url", ""))).casefold(): r
            for r in records
            if isinstance(r, dict)
        }
        fetched_at = datetime.now().isoformat(timespec="seconds")
        to_save = {}
        for url in to_fetch:
            record = by_url.get(url.casefold())
            if not record or is_error_record(record):
                reason = (record or {}).get("error") or "no data returned"
                results[url] = {
                    "ok": False,
                    "cached": False,
                    "hiring_posts": None,
                    "latest_hiring_post": None,
                    "error": str(reason),
                }
                continue
            processed = process_enrich_data(record)
            processed["fetched_at"] = fetched_at
            to_save[url] = processed
            posts, latest = _hiring_summary(processed)
            results[url] = {
                "ok": True,
                "cached": False,
                "hiring_posts": posts or 0,
                "latest_hiring_post": latest,
                "error": None,
            }
        if to_save:
            enrich_pkg.save_enrich_data(to_save)
    return results
