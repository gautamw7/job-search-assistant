#!/usr/bin/env python3
"""
Recover enrich_data.json for all missing URLs using enrich.py helpers.
Single-threaded, skip existing dict entries, append via save_enrich_data.
"""

import time

from app.core.logging import get_logger
from app.services.enrich.fetcher import fetch_enrich_data
from app.services.enrich.processor import process_enrich_data
from app.services.enrich.store import load_all_profiles, save_enrich_data
from app.services.generation import load_generated_messages
from app.services.secrets import get_brightdata_key

logger = get_logger(__name__)


def main():
    # History and the profile cache live in SQLite now (phase 4).
    gen_data = load_generated_messages()
    enrich_data = load_all_profiles()

    all_urls = sorted(set(gen_data.keys()) | set(enrich_data.keys()))
    logger.info(
        "found %s total urls (gen=%s enrich=%s)",
        len(all_urls),
        len(gen_data),
        len(enrich_data),
    )

    # Skip existing dict entries with card_info (already new format)
    targets = []
    for url in all_urls:
        existing = enrich_data.get(url)
        if isinstance(existing, dict) and "card_info" in existing:
            logger.info("skip existing url=%s (already dict)", url)
            continue
        # Also skip test dummy urls
        if url.startswith("https://www.linkedin.com/in/test"):
            logger.info("skip test url=%s", url)
            continue
        targets.append(url)

    logger.info("targets to recover: %s", targets)

    api_key = get_brightdata_key()
    if not api_key:
        logger.error("BRIGHTDATA_API_KEY missing — cannot recover")
        return 1

    logger.info("using brightdata key %s********", api_key[:4] if api_key else "")

    success = 0
    failed = []

    for url in targets:
        logger.info("recovering url=%s", url)
        try:
            results = fetch_enrich_data([url])
            if not results:
                logger.warning("no results for url=%s", url)
                failed.append(url)
                continue
            processed = process_enrich_data(results[0])
            # Sanity log
            logger.info(
                "processed url=%s hiring=%s dropped=%s people=%s",
                url,
                len(processed["activity"]["hiring"]),
                len(processed["activity"]["dropped"]),
                len(processed["discovery"]["people_also_viewed"]),
            )
            save_enrich_data({url: processed})
            logger.info("saved url=%s", url)
            success += 1
            time.sleep(2)
        except Exception as e:
            logger.exception("failed url=%s err=%s", url, e)
            failed.append(url)
            time.sleep(2)
            continue

    logger.info(
        "recover done success=%s failed=%s failed_list=%s", success, len(failed), failed
    )
    logger.info("final cached profiles=%s", len(load_all_profiles()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
