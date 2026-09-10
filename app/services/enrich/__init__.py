"""Deep enrich module — small public interface, rich internal implementation.

Public seam (what callers import):
  from app.services.enrich import get_enrich_data, cached_enrich_data

Internal seams (not part of public interface, for tests/internal use):
  enrich.fetcher, enrich.processor, enrich.store
"""

from app.services.enrich.fetcher import (
    fetch_enrich_data,
    generate_input_json,
)
from app.services.enrich.processor import (
    CARD_FIELDS,
    CONTENT_FIELDS,
    HIRING_PATTERNS,
    HIRING_REGEX,
    content_to_markdown,
    map_enrich_data_by_url,
    process_enrich_data,
)
from app.services.enrich.store import (
    cached_enrich_data,
    get_enrich_data,
    save_enrich_data,
)

__all__ = [
    "CARD_FIELDS",
    "CONTENT_FIELDS",
    "HIRING_PATTERNS",
    "HIRING_REGEX",
    "cached_enrich_data",
    "content_to_markdown",
    "fetch_enrich_data",
    "generate_input_json",
    "get_enrich_data",
    "map_enrich_data_by_url",
    "process_enrich_data",
    "save_enrich_data",
]
