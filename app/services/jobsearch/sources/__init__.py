"""Job sources share one interface so new ones (Indeed, Naukri…) are one file each."""

from app.services.jobsearch.sources.adzuna import AdzunaSource
from app.services.jobsearch.sources.apify import ApifyLinkedInSource
from app.services.jobsearch.sources.base import JobPosting, SearchQuery, SourceError

ALL_SOURCES = (AdzunaSource, ApifyLinkedInSource)

__all__ = [
    "ALL_SOURCES",
    "AdzunaSource",
    "ApifyLinkedInSource",
    "JobPosting",
    "SearchQuery",
    "SourceError",
]
