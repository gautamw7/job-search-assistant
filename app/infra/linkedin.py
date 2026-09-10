"""LinkedIn URL helpers — single source for pattern + normalization."""

import re

LINKEDIN_PATTERN = re.compile(r"^https://(www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?$")


def normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.startswith("https://"):
        url = "https://" + url.lstrip("/")
    return url


def extract_handle(url: str) -> str:
    m = re.search(r"/in/([^/?#]+)", url)
    return m.group(1) if m else url
