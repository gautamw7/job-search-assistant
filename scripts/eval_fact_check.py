#!/usr/bin/env python3
"""Fact-check saved messages and report how often they contain unsupported claims.

Grows the phase-1 evaluation notebook into a repeatable check: run it after
changing a prompt or model to see whether hallucinations went up or down.

    uv run python scripts/eval_fact_check.py --limit 20
    uv run python scripts/eval_fact_check.py --limit 20 --json report.json

Each checked message is one Gemini call (recorded in the usage ledger).
"""

import argparse
import json

from app.services.background import shared_background
from app.services.enrich import get_profile
from app.services.enrich.processor import activity_to_markdown, content_to_markdown
from app.services.factcheck import fact_check
from app.services.generation import load_generated_messages
from app.services.resources import build_resources


def _recipient_text(profile: dict) -> str:
    parts = [
        content_to_markdown(profile.get("card_info") or {}),
        content_to_markdown(profile.get("content") or {}),
        activity_to_markdown(profile.get("activity")),
    ]
    return "\n\n".join(p for p in parts if p)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=10, help="max messages to check")
    parser.add_argument("--json", help="write the full report to this file")
    args = parser.parse_args()

    resume = build_resources()["user_resume"]
    rows = []
    for url, entry in load_generated_messages().items():
        generations = (entry or {}).get("generations") or []
        if not generations:
            continue
        latest = generations[-1]
        profile = get_profile(url)
        if not profile:
            continue
        result = fact_check(
            latest["generated_message"],
            user_resume=resume,
            recipient=_recipient_text(profile),
            user_note=latest.get("user_note"),
            hooks=shared_background(resume, profile),
        )
        rows.append({"linkedin_url": url, **result})
        mark = {"pass": "ok ", "flagged": "!! ", "error": "?? "}.get(
            result["status"], "-- "
        )
        print(f"{mark}{url}")
        for issue in result["issues"]:
            print(f"     - {issue['claim']}  ({issue['reason']})")
        if len(rows) >= args.limit:
            break

    checked = [r for r in rows if r["status"] in ("pass", "flagged")]
    flagged = [r for r in checked if r["status"] == "flagged"]
    rate = len(flagged) / len(checked) if checked else 0.0
    print(
        f"\nchecked={len(checked)} flagged={len(flagged)} flag_rate={rate:.0%} errors={len(rows) - len(checked)}"
    )
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"flag_rate": rate, "results": rows}, f, indent=2)


if __name__ == "__main__":
    main()
