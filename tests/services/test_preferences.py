"""Questionnaire answers -> source-specific search options."""

from app.services.jobsearch.preferences import (
    SENIORITY_TO_EXPERIENCE,
    adzuna_params,
    linkedin_params,
    source_notes,
)
from app.services.jobsearch.profile import SearchProfile
from app.services.jobsearch.sources.base import SearchQuery


def _q(**kw):
    base = {"titles": ["Data Scientist"], "countries": ["de"], "max_days_old": 30}
    return SearchQuery(**{**base, **kw})


def test_linkedin_maps_job_type_experience_remote_and_recency():
    params = linkedin_params(
        _q(
            employment_types=["full_time", "contract"],
            experience_levels=["entry", "mid_senior"],
            remote="hybrid",
            posted_days=7,
        )
    )
    assert params == {"f_TPR": "r604800", "f_JT": "F,C", "f_E": "2,4", "f_WT": "3"}


def test_no_answers_means_no_filters_on_linkedin():
    assert linkedin_params(_q()) == {"f_TPR": "r2592000"}  # only the 30-day source cap


def test_recency_never_exceeds_the_source_cap():
    assert linkedin_params(_q(posted_days=14, max_days_old=7))["f_TPR"] == "r604800"


def test_adzuna_flags_only_when_exactly_one_contract_type_and_salary_matches_currency():
    one = adzuna_params(
        _q(
            employment_types=["part_time"],
            salary_min=40000,
            salary_currency="EUR",
            posted_days=14,
        ),
        "de",
    )
    assert one == {"max_days_old": 14, "part_time": 1, "salary_min": 40000}
    several = adzuna_params(_q(employment_types=["full_time", "contract"]), "de")
    assert (
        "full_time" not in several and "contract" not in several
    )  # Adzuna can't OR them
    other_currency = adzuna_params(_q(salary_min=40000, salary_currency="EUR"), "in")
    assert "salary_min" not in other_currency  # India's salaries are in INR


def test_source_limits_are_explained_not_silent():
    notes = " ".join(
        source_notes(
            _q(
                experience_levels=["internship"],
                employment_types=["full_time", "part_time"],
            )
        )
    )
    assert "internship" in notes and "one contract type" in notes


def test_suggested_experience_follows_seniority():
    assert SENIORITY_TO_EXPERIENCE["junior"] == ["entry", "associate"]


def test_profile_defaults_keep_old_saved_profiles_valid():
    old = SearchProfile.model_validate(
        {"titles": ["Data Scientist"], "countries": ["de"]}
    )
    assert (
        old.employment_types == []
        and old.experience_levels == []
        and old.posted_within_days == 30
    )
