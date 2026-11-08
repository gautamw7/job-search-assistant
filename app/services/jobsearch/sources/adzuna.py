"""Adzuna job search API (free). Returns description snippets only, and its terms
require an "Adzuna" link on each displayed advert (the UI shows "via Adzuna")."""

import requests

from app.core.logging import get_logger
from app.services import usage
from app.services.jobsearch.preferences import CURRENCY, adzuna_params
from app.services.jobsearch.profile import ADZUNA_COUNTRIES
from app.services.jobsearch.sources.base import (
    JobPosting,
    JobSource,
    SearchQuery,
    SourceError,
)
from app.services.secrets import get_adzuna_credentials

logger = get_logger(__name__)

API = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
TIMEOUT = (10, 30)


def _to_posting(item: dict, country: str) -> JobPosting:
    company = (item.get("company") or {}).get("display_name") or ""
    location = (item.get("location") or {}).get("display_name") or ""
    return JobPosting(
        source="adzuna",
        external_id=str(item.get("id", "")),
        title=(item.get("title") or "").strip(),
        company=company.strip(),
        location=location.strip(),
        country=country,
        description=(item.get("description") or "").strip(),
        description_is_snippet=True,
        url=item.get("redirect_url") or "",
        posted_at=item.get("created"),
        salary_min=item.get("salary_min"),
        salary_max=item.get("salary_max"),
        salary_currency=CURRENCY.get(country),
        employment_type=item.get("contract_time") or item.get("contract_type"),
    )


class AdzunaSource(JobSource):
    name = "adzuna"

    def available(self) -> bool:
        return get_adzuna_credentials() is not None

    def search(
        self, query: SearchQuery, results_per_query: int = 50
    ) -> list[JobPosting]:
        creds = get_adzuna_credentials()
        if not creds:
            raise SourceError("Adzuna keys are not set (Settings → Adzuna).")
        app_id, app_key = creds
        postings: list[JobPosting] = []
        countries = [c for c in query.countries if c in ADZUNA_COUNTRIES]
        for country in countries:
            for title in query.titles:
                params = {
                    "app_id": app_id,
                    "app_key": app_key,
                    "what_phrase": title,
                    "results_per_page": results_per_query,
                    "sort_by": "relevance",
                    "content-type": "application/json",
                    **adzuna_params(query, country),
                }
                try:
                    resp = requests.get(
                        API.format(country=country), params=params, timeout=TIMEOUT
                    )
                except requests.RequestException as e:
                    raise SourceError(f"Adzuna unreachable: {e}") from e
                usage.record_adzuna(1)
                if resp.status_code in (401, 403):
                    raise SourceError("Adzuna rejected the keys (check Settings).")
                if resp.status_code == 429:
                    raise SourceError("Adzuna rate limit reached; try again later.")
                if not resp.ok:
                    logger.warning(
                        "adzuna %s %s failed status=%s",
                        country,
                        title,
                        resp.status_code,
                    )
                    continue
                results = resp.json().get("results") or []
                postings += [_to_posting(r, country) for r in results if r.get("title")]
        logger.info(
            "adzuna returned %s postings for %s countries",
            len(postings),
            len(countries),
        )
        return postings
