"""LinkedIn jobs via an Apify actor (default ``curious_coder/linkedin-jobs-scraper``).

The actor is given LinkedIn job-search URLs; it returns full descriptions plus company
size, applicants and seniority. Charged per result, so the total is capped per search.
Field names differ between actors, so the mapping accepts common alternatives.
"""

from urllib.parse import urlencode

import requests

from app.core.logging import get_logger
from app.services import usage
from app.services.jobsearch.preferences import linkedin_params
from app.services.jobsearch.profile import COUNTRY_NAMES
from app.services.jobsearch.sources.base import (
    JobPosting,
    JobSource,
    SearchQuery,
    SourceError,
)
from app.services.secrets import get_apify_token

logger = get_logger(__name__)

DEFAULT_ACTOR = "curious_coder~linkedin-jobs-scraper"
RUN_URL = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
SYNC_TIMEOUT_S = 280  # the sync endpoint gives up at 300 s


def _first(item: dict, *keys, default=None):
    for key in keys:
        value = item.get(key)
        if value not in (None, "", []):
            return value
    return default


def _to_int(value) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        digits = "".join(ch for ch in value.split("-")[0] if ch.isdigit())
        return int(digits) if digits else None
    return None


def search_url(titles: list[str], country: str, extra: dict) -> str:
    params = {
        "keywords": " OR ".join(f'"{t}"' for t in titles),
        "location": COUNTRY_NAMES.get(country, country.upper()),
        "sortBy": "R",
        **extra,
    }
    return "https://www.linkedin.com/jobs/search/?" + urlencode(params)


def _to_posting(item: dict, country: str) -> JobPosting:
    workplace = str(_first(item, "workplaceTypes", "workType", default="")).lower()
    remote = (
        "remote"
        if "remote" in workplace or item.get("workRemoteAllowed")
        else (
            "hybrid"
            if "hybrid" in workplace
            else ("onsite" if "site" in workplace else None)
        )
    )
    description = _first(
        item, "descriptionText", "description", "jobDescription", default=""
    )
    return JobPosting(
        source="apify",
        external_id=str(_first(item, "id", "jobId", "trackingId", default="")),
        title=str(_first(item, "title", "jobTitle", default="")).strip(),
        company=str(_first(item, "companyName", "company", default="")).strip(),
        location=str(_first(item, "location", "jobLocation", default="")).strip(),
        country=country,
        description=str(description).strip(),
        description_is_snippet=len(str(description)) < 600,
        url=str(_first(item, "link", "jobUrl", "url", default="")),
        posted_at=_first(item, "postedAt", "publishedAt", "postedDate"),
        seniority=_first(item, "seniorityLevel", "experienceLevel"),
        employment_type=_first(item, "employmentType", "contractType"),
        remote=remote,
        company_size=_to_int(
            _first(item, "companyEmployeesCount", "companyEmployeeCount", "companySize")
        ),
        company_url=_first(item, "companyLinkedinUrl", "companyUrl"),
        applicants=_to_int(_first(item, "applicantsCount", "applicationsCount")),
    )


class ApifyLinkedInSource(JobSource):
    name = "apify"

    def __init__(self, actor: str = DEFAULT_ACTOR):
        self.actor = actor

    def available(self) -> bool:
        return get_apify_token() is not None

    def search(self, query: SearchQuery, max_results: int = 50) -> list[JobPosting]:
        token = get_apify_token()
        if not token:
            raise SourceError("Apify token is not set (Settings → Apify).")
        if max_results <= 0 or not query.countries:
            return []
        usage.check_budget(apify_results=max_results)
        per_country = max(1, max_results // len(query.countries))
        urls = [
            search_url(query.titles, c, linkedin_params(query)) for c in query.countries
        ]
        payload = {
            "urls": urls,
            "scrapeCompany": True,
            "count": per_country,
            "limitPerSource": per_country,
        }
        try:
            resp = requests.post(
                RUN_URL.format(actor=self.actor),
                params={
                    "timeout": SYNC_TIMEOUT_S,
                    "limit": max_results,
                    "format": "json",
                },
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=SYNC_TIMEOUT_S + 20,
            )
        except requests.Timeout as e:
            raise SourceError(
                "LinkedIn search via Apify took too long; showing other sources."
            ) from e
        except requests.RequestException as e:
            raise SourceError(f"Apify unreachable: {e}") from e
        if resp.status_code in (401, 403):
            raise SourceError("Apify rejected the token (check Settings).")
        if resp.status_code == 402 or "not-enough-usage" in resp.text[:500]:
            raise SourceError(
                "Apify credit is used up for this month; showing Adzuna results only."
            )
        if resp.status_code == 408:
            raise SourceError(
                "LinkedIn search via Apify timed out; showing other sources."
            )
        if not resp.ok:
            raise SourceError(
                f"Apify run failed ({resp.status_code}): {resp.text[:200]}"
            )
        items = resp.json()
        items = items if isinstance(items, list) else []
        usage.record_apify(len(items))
        # The actor doesn't echo which search URL an item came from; infer country from
        # its location text, falling back to the first target country.
        postings = []
        for item in items[:max_results]:
            location = str(_first(item, "location", default="")).lower()
            country = next(
                (
                    c
                    for c in query.countries
                    if COUNTRY_NAMES.get(c, "").lower() in location
                ),
                query.countries[0],
            )
            posting = _to_posting(item, country)
            if posting.title:
                postings.append(posting)
        logger.info("apify returned %s postings", len(postings))
        return postings
