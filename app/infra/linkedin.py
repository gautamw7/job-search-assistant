"""LinkedIn URL helpers — single source for pattern + normalization.

All history/cache keys use the canonical form ``https://www.linkedin.com/in/<handle>``
so trailing slashes, ``http://``, country subdomains and tracking query strings
never create duplicate cache entries (each duplicate is a paid BrightData fetch).
"""

import re
from urllib.parse import urlsplit

# Accepts any reasonable user-pasted profile URL (scheme optional, subdomain optional,
# query/fragment/trailing slash allowed). Handles may be percent-encoded unicode.
LINKEDIN_PATTERN = re.compile(
    r"^(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/[^/?#\s]+/?(?:[?#].*)?$",
    re.IGNORECASE,
)

_CANONICAL_PREFIX = "https://www.linkedin.com/in/"


def extract_handle(url: str) -> str:
    m = re.search(r"/in/([^/?#]+)", url)
    return m.group(1) if m else url


def is_linkedin_profile_url(url: str) -> bool:
    return bool(LINKEDIN_PATTERN.match(url.strip()))


def normalize_url(url: str) -> str:
    """Return the canonical profile URL, or the stripped input if it isn't one."""
    url = url.strip()
    if not LINKEDIN_PATTERN.match(url):
        return url
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url.lstrip("/")
    path = urlsplit(url).path
    handle = extract_handle(path).rstrip("/")
    return f"{_CANONICAL_PREFIX}{handle}"
