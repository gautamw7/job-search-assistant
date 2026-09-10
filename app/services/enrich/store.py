"""Internal: enrich persistence — save/load/merge + cache helpers."""

import json
from pathlib import Path

from app.services.enrich.processor import process_enrich_data
from app.services.logger import get_logger

logger = get_logger(__name__)


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
    from app.services.paths import DATA_DIR

    if output_path is None or output_path == "data/enrich_data.json":
        path = DATA_DIR / "enrich_data.json"
    else:
        path = Path(output_path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    existing = load_enrichment_store(path)

    for url, new_data in enrich_data.items():
        if url not in existing or not isinstance(existing[url], dict) or isinstance(existing[url], str):
            existing[url] = new_data
            continue
        old = existing[url]
        old_card = old.get("card_info", {})
        new_card = new_data.get("card_info", {})
        old["card_info"] = {**old_card, **new_card}

        old_content = old.get("content", {})
        new_content = new_data.get("content", {})
        for k, v in new_content.items():
            if k not in old_content:
                old_content[k] = v
            elif isinstance(v, list) and isinstance(old_content[k], list):
                existing_ids = {json.dumps(x, sort_keys=True) for x in old_content[k] if isinstance(x, dict)}
                for item in v:
                    key = json.dumps(item, sort_keys=True) if isinstance(item, dict) else str(item)
                    if key not in existing_ids:
                        old_content[k].append(item)
            elif isinstance(v, dict) and isinstance(old_content[k], dict):
                old_content[k] = {**old_content[k], **v}
            else:
                old_content[k] = v
        old["content"] = old_content

        old_act = old.get("activity", {"hiring": [], "dropped": []})
        new_act = new_data.get("activity", {"hiring": [], "dropped": []})
        for key in ("hiring", "dropped"):
            old_list = old_act.get(key, []) if isinstance(old_act.get(key), list) else []
            new_list = new_act.get(key, []) if isinstance(new_act.get(key), list) else []
            seen = {json.dumps(x, sort_keys=True) for x in old_list}
            for item in new_list:
                j = json.dumps(item, sort_keys=True)
                if j not in seen:
                    old_list.append(item)
                    seen.add(j)
            old_act[key] = old_list
        old["activity"] = old_act

        old_disc = old.get("discovery", {"people_also_viewed": []})
        new_disc = new_data.get("discovery", {"people_also_viewed": []})
        old_people = old_disc.get("people_also_viewed", []) if isinstance(old_disc.get("people_also_viewed"), list) else []
        new_people = new_disc.get("people_also_viewed", []) if isinstance(new_disc.get("people_also_viewed"), list) else []
        seen_links = {p.get("profile_link") for p in old_people if isinstance(p, dict)}
        for p in new_people:
            if isinstance(p, dict) and p.get("profile_link") not in seen_links:
                old_people.append(p)
                seen_links.add(p.get("profile_link"))
        old_disc["people_also_viewed"] = old_people
        old["discovery"] = old_disc

        old_drop = old.get("dropped_fields", {})
        new_drop = new_data.get("dropped_fields", {})
        if isinstance(old_drop, dict) and isinstance(new_drop, dict):
            old_drop.update(new_drop)
            old["dropped_fields"] = old_drop
        existing[url] = old

    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4)
    logger.info("enrich data saved path=%s entries=%s", path, len(enrich_data))


def cached_enrich_data(linkedin_url: str) -> dict:
    from app.services.paths import ENRICH_DATA

    path = ENRICH_DATA
    existing = load_enrichment_store(path)
    cached = existing.get(linkedin_url, {})
    if isinstance(cached, dict) and (cached.get("content") or cached.get("card_info")):
        return cached
    return {}


def get_enrich_data(linkedin_url: str, force_refresh: bool = False) -> str:
    from app.services.enrich.processor import content_to_markdown

    logger.info("get_enrich_data start url=%s force_refresh=%s", linkedin_url, force_refresh)
    cached = None if force_refresh else cached_enrich_data(linkedin_url)
    if cached:
        logger.info("cached enrich data found url=%s", linkedin_url)
        processed = cached
    else:
        # Import via package so patching services.enrich.fetch_enrich_data works in tests
        import app.services.enrich as enrich_pkg

        results = enrich_pkg.fetch_enrich_data([linkedin_url])
        if not results:
            logger.warning("no enrichment data found url=%s", linkedin_url)
            return ""
        processed = process_enrich_data(results[0])
        enrich_pkg.save_enrich_data({linkedin_url: processed})

    content_md = content_to_markdown(processed.get("content", {}))
    card_info_md = content_to_markdown(processed.get("card_info", {}))
    content = f"# Card Info\n{card_info_md}\n\n# Content\n{content_md}".strip()

    activity_hiring = processed.get("activity", {}).get("hiring", []) if isinstance(processed.get("activity"), dict) else []
    activity_dropped = processed.get("activity", {}).get("dropped", []) if isinstance(processed.get("activity"), dict) else []
    discovery_people = processed.get("discovery", {}).get("people_also_viewed", []) if isinstance(processed.get("discovery"), dict) else []

    logger.info(
        "get_enrich_data done url=%s content_md_len=%s hiring=%s dropped=%s people=%s",
        linkedin_url,
        len(content),
        len(activity_hiring),
        len(activity_dropped),
        len(discovery_people),
    )
    return content
