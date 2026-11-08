"""Fetch a job's full description when a source gave only a snippet (Adzuna)."""

import html
import re

import requests

from app.core.logging import get_logger

logger = get_logger(__name__)

TIMEOUT = (8, 15)
MAX_CHARS = 8000
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) JobSearchAssistant/0.1",
    "Accept-Language": "en",
}


def html_to_text(raw: str) -> str:
    raw = re.sub(
        r"(?is)<(script|style|noscript|svg|header|footer|nav)[^>]*>.*?</\1>", " ", raw
    )
    raw = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6])>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    lines = [re.sub(r"[ \t\xa0]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _best_block(text: str, title: str) -> str:
    """Keep the part of the page around the job title (pages carry lots of chrome)."""
    lowered = text.casefold()
    anchor = lowered.find((title or "").casefold()[:40]) if title else -1
    start = max(0, anchor - 200) if anchor >= 0 else 0
    return text[start : start + MAX_CHARS]


def fetch_full_description(url: str, title: str, snippet: str) -> str | None:
    """Full text, or None if the page can't be read or isn't clearly better."""
    if not url:
        return None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException as e:
        logger.info("full description fetch failed url=%s err=%s", url, e)
        return None
    if not resp.ok or "html" not in resp.headers.get("Content-Type", ""):
        return None
    text = _best_block(html_to_text(resp.text), title)
    # Must be substantially longer than the snippet and mention the role.
    title_words = set(re.findall(r"[a-z]{4,}", (title or "").casefold()))
    if len(text) < max(800, 2 * len(snippet or "")) or (
        title_words and not any(w in text.casefold() for w in title_words)
    ):
        return None
    return text
