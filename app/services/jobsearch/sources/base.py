"""Common types for job sources."""

from dataclasses import dataclass, field


class SourceError(RuntimeError):
    """A source could not run (missing key, out of credit…). Shown as a notice."""


@dataclass
class SearchQuery:
    titles: list[str]
    countries: list[str]  # ISO-2 lower case, most preferred first
    max_days_old: int = 30
    remote: str = "any"
    employment_types: list[str] = field(default_factory=list)
    experience_levels: list[str] = field(default_factory=list)
    posted_days: int | None = None  # user's recency choice (capped by max_days_old)
    salary_min: float | None = None
    salary_currency: str | None = None
    exclude_terms: str | None = None  # title words to leave out (above-level roles)


@dataclass
class JobPosting:
    source: str
    external_id: str
    title: str
    company: str
    location: str
    country: str
    description: str
    description_is_snippet: bool
    url: str
    posted_at: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    remote: str | None = None
    seniority: str | None = None
    employment_type: str | None = None
    company_size: int | None = None
    company_url: str | None = None
    applicants: int | None = None
    extra: dict = field(default_factory=dict)


class JobSource:
    name = "base"

    def available(self) -> bool:
        raise NotImplementedError

    def search(self, query: SearchQuery) -> list[JobPosting]:
        raise NotImplementedError
