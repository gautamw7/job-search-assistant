"""Job-type questionnaire answers -> concrete search options for each source.

The questions are defined once here (served to the UI in /jobs/meta). Each source
only supports some filters, so answers that a source can't express become notes
shown to the user instead of silently ignored.
"""

from app.services.jobsearch.sources.base import SearchQuery

QUESTIONS = [
    {
        "id": "employment_types",
        "label": "What kind of contract?",
        "multi": True,
        "options": [
            {"value": "full_time", "label": "Full-time"},
            {"value": "part_time", "label": "Part-time"},
            {"value": "contract", "label": "Contract / freelance"},
        ],
    },
    {
        "id": "experience_levels",
        "label": "Which experience levels?",
        "multi": True,
        "options": [
            {"value": "internship", "label": "Internship"},
            {"value": "entry", "label": "Entry level"},
            {"value": "associate", "label": "Associate"},
            {"value": "mid_senior", "label": "Mid-senior"},
            {"value": "director", "label": "Lead / director"},
        ],
    },
    {
        "id": "remote",
        "label": "Where do you want to work?",
        "multi": False,
        "options": [
            {"value": "any", "label": "Anywhere"},
            {"value": "remote", "label": "Remote"},
            {"value": "hybrid", "label": "Hybrid"},
            {"value": "onsite", "label": "On-site"},
        ],
    },
    {
        "id": "posted_within_days",
        "label": "How recent should postings be?",
        "multi": False,
        "options": [
            {"value": 7, "label": "Last 7 days"},
            {"value": 14, "label": "Last 14 days"},
            {"value": 30, "label": "Last 30 days"},
        ],
    },
]

# Default experience levels suggested from the resume's seniority (user can change).
SENIORITY_TO_EXPERIENCE = {
    "intern": ["internship"],
    "entry": ["entry"],
    "junior": ["entry", "associate"],
    "mid": ["associate", "mid_senior"],
    "senior": ["mid_senior", "director"],
}

# LinkedIn's public search-URL codes (f_JT, f_E, f_WT).
LINKEDIN_JOB_TYPE = {
    "full_time": "F",
    "part_time": "P",
    "contract": "C",
    "internship": "I",
}
LINKEDIN_EXPERIENCE = {
    "internship": "1",
    "entry": "2",
    "associate": "3",
    "mid_senior": "4",
    "director": "5",
}
LINKEDIN_WORK_TYPE = {"onsite": "1", "remote": "2", "hybrid": "3"}

# Adzuna takes one boolean flag per contract type; it has no internship or remote filter.
ADZUNA_FLAG = {
    "full_time": "full_time",
    "part_time": "part_time",
    "contract": "contract",
}

# Adzuna salaries are in each country's currency.
CURRENCY = {
    "de": "EUR",
    "at": "EUR",
    "fr": "EUR",
    "es": "EUR",
    "it": "EUR",
    "nl": "EUR",
    "be": "EUR",
    "in": "INR",
    "gb": "GBP",
    "us": "USD",
    "ca": "CAD",
    "au": "AUD",
    "ch": "CHF",
    "pl": "PLN",
    "sg": "SGD",
    "nz": "NZD",
    "za": "ZAR",
    "br": "BRL",
    "mx": "MXN",
}


def _days(query: SearchQuery) -> int:
    requested = query.posted_days or query.max_days_old
    return max(1, min(int(requested), int(query.max_days_old)))


def linkedin_params(query: SearchQuery) -> dict:
    """Extra LinkedIn search-URL parameters for this query."""
    params = {"f_TPR": f"r{_days(query) * 86400}"}
    job_types = [
        LINKEDIN_JOB_TYPE[t] for t in query.employment_types if t in LINKEDIN_JOB_TYPE
    ]
    if job_types:
        params["f_JT"] = ",".join(dict.fromkeys(job_types))
    levels = [
        LINKEDIN_EXPERIENCE[e]
        for e in query.experience_levels
        if e in LINKEDIN_EXPERIENCE
    ]
    if levels:
        params["f_E"] = ",".join(dict.fromkeys(levels))
    if query.remote in LINKEDIN_WORK_TYPE:
        params["f_WT"] = LINKEDIN_WORK_TYPE[query.remote]
    return params


def adzuna_params(query: SearchQuery, country: str) -> dict:
    """Extra Adzuna search parameters for this query and country."""
    params: dict = {"max_days_old": _days(query)}
    flags = [ADZUNA_FLAG[t] for t in query.employment_types if t in ADZUNA_FLAG]
    if len(flags) == 1:
        params[flags[0]] = 1
    if (
        query.salary_min
        and query.salary_currency
        and CURRENCY.get(country) == query.salary_currency
    ):
        params["salary_min"] = int(query.salary_min)
    if query.exclude_terms:
        params["what_exclude"] = query.exclude_terms
    return params


def source_notes(query: SearchQuery) -> list[str]:
    """Answers a source can't express, shown to the user once per search."""
    notes = []
    if len([t for t in query.employment_types if t in ADZUNA_FLAG]) > 1:
        notes.append(
            "Adzuna can filter one contract type at a time, so it shows all types."
        )
    if "internship" in query.experience_levels:
        notes.append(
            "Adzuna has no internship filter, so internships come from LinkedIn only."
        )
    if query.salary_min and query.salary_currency:
        notes.append(
            f"Salary filter applies to Adzuna countries that use {query.salary_currency}; "
            "other countries are not filtered by salary."
        )
    return notes
