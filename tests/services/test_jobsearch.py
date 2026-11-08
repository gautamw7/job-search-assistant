"""Phase 2: sources, dedupe, ranking, details, review, profile and the pipeline."""

import json
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.core.settings import DATA_DIR
from app.infra import db
from app.services.jobsearch import details, pipeline, ranking, store
from app.services.jobsearch import profile as profile_svc
from app.services.jobsearch.preferences import linkedin_params
from app.services.jobsearch.profile import SearchProfile
from app.services.jobsearch.sources import (
    AdzunaSource,
    ApifyLinkedInSource,
    SearchQuery,
    SourceError,
)
from app.services.jobsearch.sources.apify import search_url
from app.services.jobsearch.sources.base import JobPosting
from app.services.structured_resume import StructuredResume, markdown_hash
from app.services.structured_resume import save as save_resume


@pytest.fixture(autouse=True)
def fresh_db():
    (DATA_DIR / "app.db").unlink(missing_ok=True)
    for suffix in ("-wal", "-shm"):
        (DATA_DIR / f"app.db{suffix}").unlink(missing_ok=True)
    db._migrated_paths.clear()
    (DATA_DIR / "usage.json").unlink(missing_ok=True)
    (DATA_DIR / "settings.json").unlink(missing_ok=True)
    pipeline._runs.clear()
    yield


def _resp(code=200, payload=None, text=""):
    r = MagicMock()
    r.status_code, r.ok = code, 200 <= code < 300
    r.json.return_value = payload
    r.text = text or json.dumps(payload or {})
    r.headers = {"Content-Type": "text/html"}
    return r


PROFILE = SearchProfile(
    titles=["Data Scientist", "ML Engineer"],
    seniority="entry",
    skills=["Python", "SQL", "PyTorch", "XGBoost"],
    countries=["de", "in"],
    company_types=["startup"],
    needs_sponsorship=True,
    languages=[{"name": "English", "level": "C1"}, {"name": "German", "level": "A2"}],
)


def _posting(**kw):
    base = {
        "source": "adzuna",
        "external_id": "1",
        "title": "Data Scientist",
        "company": "Acme GmbH",
        "location": "Berlin, Germany",
        "country": "de",
        "description": "Python SQL",
        "description_is_snippet": True,
        "url": "https://adzuna/1",
    }
    return JobPosting(**{**base, **kw})


# ---- sources -------------------------------------------------------------------


def test_adzuna_maps_results_and_skips_unsupported_countries():
    item = {
        "id": 9,
        "title": "Data Scientist (m/w/d)",
        "company": {"display_name": "Acme"},
        "location": {"display_name": "Berlin"},
        "description": "We use Python",
        "redirect_url": "https://www.adzuna.de/x",
        "created": "2026-11-01T10:00:00Z",
        "salary_min": 50000,
    }
    with (
        patch(
            "app.services.jobsearch.sources.adzuna.get_adzuna_credentials",
            return_value=("id", "key"),
        ),
        patch(
            "app.services.jobsearch.sources.adzuna.requests.get",
            return_value=_resp(200, {"results": [item]}),
        ) as get,
    ):
        out = AdzunaSource().search(
            SearchQuery(titles=["Data Scientist"], countries=["de", "in", "ie"])
        )
    assert get.call_count == 1  # Adzuna searches India only in this app
    assert "/in/search/" in get.call_args.args[0]
    assert (
        out[0].company == "Acme"
        and out[0].salary_currency == "INR"
        and out[0].description_is_snippet
    )


def test_adzuna_bad_keys_become_a_source_error():
    with (
        patch(
            "app.services.jobsearch.sources.adzuna.get_adzuna_credentials",
            return_value=("id", "key"),
        ),
        patch(
            "app.services.jobsearch.sources.adzuna.requests.get",
            return_value=_resp(401, {}),
        ),
        pytest.raises(SourceError, match="rejected"),
    ):
        AdzunaSource().search(SearchQuery(titles=["x"], countries=["in"]))


def test_apify_maps_linkedin_fields_and_handles_no_credit():
    item = {
        "id": "77",
        "title": "ML Engineer",
        "companyName": "TinyAI",
        "location": "Munich, Germany",
        "descriptionText": "x" * 900,
        "link": "https://linkedin.com/jobs/77",
        "postedAt": "2026-11-05",
        "seniorityLevel": "Entry level",
        "companyEmployeesCount": 45,
        "applicantsCount": "12 applicants",
        "workplaceTypes": ["Remote"],
    }
    with (
        patch(
            "app.services.jobsearch.sources.apify.get_apify_token", return_value="tok"
        ),
        patch(
            "app.services.jobsearch.sources.apify.requests.post",
            return_value=_resp(200, [item]),
        ) as post,
    ):
        out = ApifyLinkedInSource().search(
            SearchQuery(titles=["ML Engineer"], countries=["de"]), max_results=10
        )
    p = out[0]
    assert (p.company_size, p.applicants, p.remote, p.country) == (
        45,
        12,
        "remote",
        "de",
    )
    assert not p.description_is_snippet
    assert post.call_args.kwargs["params"]["limit"] == 10
    with (
        patch(
            "app.services.jobsearch.sources.apify.get_apify_token", return_value="tok"
        ),
        patch(
            "app.services.jobsearch.sources.apify.requests.post",
            return_value=_resp(402, {}, "not-enough-usage"),
        ),
        pytest.raises(SourceError, match="credit"),
    ):
        ApifyLinkedInSource().search(SearchQuery(titles=["x"], countries=["de"]))


def test_linkedin_search_url_has_filters():
    query = SearchQuery(
        titles=["Data Scientist"], countries=["de"], max_days_old=30, remote="remote"
    )
    url = search_url(["Data Scientist", "ML Engineer"], "de", linkedin_params(query))
    assert "location=Germany" in url and "f_TPR=r2592000" in url and "f_WT=2" in url
    assert "f_JT" not in url  # no job-type answers given, so no job-type filter


# ---- store / dedupe ------------------------------------------------------------


def test_same_job_from_two_sources_is_merged_keeping_the_richer_copy():
    ids = store.upsert_postings([_posting(title="Data Scientist (m/w/d)")])
    ids2 = store.upsert_postings(
        [
            _posting(
                source="apify",
                title="Data Scientist",
                company="Acme",
                description="full " * 300,
                description_is_snippet=False,
                url="https://linkedin/1",
                company_size=40,
            )
        ]
    )
    assert ids == ids2
    job = store.get_jobs(ids)[0]
    assert {s["source"] for s in job["sources"]} == {"adzuna", "apify"}
    assert job["company_size"] == 40 and not job["description_is_snippet"]
    assert job["url"] == "https://linkedin/1"


def test_dismissed_jobs_stay_hidden_when_found_again():
    [job_id] = store.upsert_postings([_posting()])
    store.set_status(job_id, "dismissed")
    assert store.upsert_postings([_posting()]) == []
    assert store.get_jobs() == []
    with pytest.raises(ValueError):
        store.set_status(job_id, "archived")


# ---- ranking -------------------------------------------------------------------


def test_factors():
    assert ranking.title_match("Senior Data Scientist", ["Data Scientist"]) == 1.0
    assert ranking.title_match("Backend Developer", ["Data Scientist"]) == 0.0
    assert ranking.skills_match(
        "We use python and SQL daily", ["Python", "SQL", "Go"]
    ) == pytest.approx(2 / 3, 0.01)
    assert ranking.seniority_fit({"title": "Senior ML Engineer"}, "entry") == 0.1
    assert ranking.seniority_fit({"title": "Junior Data Scientist"}, "entry") == 0.6
    assert ranking.location_fit({"country": "de"}, PROFILE) == 1.0
    assert ranking.location_fit({"country": "in"}, PROFILE) == 0.8
    assert ranking.startup_fit({"company_size": 40}, PROFILE, 200) == 1.0
    assert ranking.startup_fit({"company_size": 5000}, PROFILE, 200) == 0.2
    recent = (datetime.now() - timedelta(days=3)).isoformat()
    assert ranking.recency({"posted_at": recent}, 30) == pytest.approx(0.9, 0.01)


def test_review_blends_fit_and_penalizes_german_gap_and_no_sponsorship():
    score, breakdown = ranking.apply_review(
        60,
        {},
        {
            "fit": 80,
            "german_required": "yes",
            "german_level": "C1",
            "sponsorship": "no",
        },
        PROFILE,
    )
    assert breakdown["penalties"] == {"german": -25, "sponsorship": -20}
    assert score == pytest.approx(0.5 * 60 + 0.5 * 80 - 45)
    ok, _ = ranking.apply_review(
        60, {}, {"fit": 80, "german_required": "yes", "german_level": "A1"}, PROFILE
    )
    assert ok == 70  # A2 speaker meets an A1 requirement


# ---- details -------------------------------------------------------------------


def test_full_description_extracted_and_rejected_when_not_better():
    page = (
        "<html><nav>menu</nav><h1>Data Scientist</h1>"
        + "<p>We need Python and SQL skills.</p>" * 60
        + "<script>x()</script></html>"
    )
    with patch(
        "app.services.jobsearch.details.requests.get",
        return_value=_resp(200, None, page),
    ) as get:
        get.return_value.text = page
        text = details.fetch_full_description("https://x", "Data Scientist", "short")
    assert text and "menu" not in text and "x()" not in text and "Python" in text
    with patch(
        "app.services.jobsearch.details.requests.get",
        return_value=_resp(200, None, "<p>tiny</p>"),
    ) as get:
        get.return_value.text = "<p>tiny</p>"
        assert (
            details.fetch_full_description("https://x", "Data Scientist", "short")
            is None
        )


# ---- LLM rate limit retry --------------------------------------------------------


def test_rate_limited_call_is_retried_then_succeeds(monkeypatch):
    from app.services.generation import llm

    monkeypatch.setattr(llm, "RATE_LIMIT_WAITS_S", (0, 0))
    err = Exception("429")
    err.code = 429
    client = MagicMock()
    ok = MagicMock(text="fine", usage_metadata=None)
    client.models.generate_content.side_effect = [err, err, ok]
    with patch.object(llm, "_client", return_value=client):
        assert llm.generate_with_fallback("hi") == "fine"
    client.models.generate_content.side_effect = err
    with (
        patch.object(llm, "_client", return_value=client),
        pytest.raises(llm.LLMError, match="free-tier limit"),
    ):
        llm.generate_with_fallback("hi")


# ---- profile + pipeline -----------------------------------------------------------


RESUME = StructuredResume.model_validate(
    {
        "contact": {"name": "Alex"},
        "experience": [
            {"title": "ML Intern", "company": "Acme", "bullets": ["PyTorch models"]}
        ],
        "skills": [{"category": "Lang", "items": ["Python", "SQL"]}],
    }
)


def test_profile_suggestion_is_sanitized():
    raw = json.dumps(
        {
            "titles": ["Data Scientist"] * 2 + ["A", "B", "C", "D", "E"],
            "seniority": "wizard",
            "countries": ["DE", "uk", "germany"],
            "company_types": ["startup", "bogus"],
            "remote": "maybe",
            "questions": [
                {"id": "q", "question": "Relocate?", "options": ["yes", "no"]}
            ]
            * 5,
        }
    )
    with patch("app.services.generation.llm.generate_with_fallback", return_value=raw):
        prof, questions = profile_svc.suggest(RESUME, "move to Germany")
    assert prof.titles[:1] == ["Data Scientist"] and len(prof.titles) <= 5
    assert prof.seniority == "entry" and prof.countries == ["de", "gb"]
    assert (
        prof.company_types == ["startup"]
        and prof.remote == "any"
        and len(questions) == 3
    )


def _wait(search_id):
    for _ in range(200):
        run = pipeline.get_search(search_id)
        if run["status"] != "running":
            return run
        time.sleep(0.02)
    raise AssertionError("search did not finish")


def test_pipeline_end_to_end_with_mocked_services():
    save_resume(RESUME, markdown_hash("x"), confirmed=True)
    profile_svc.save(PROFILE, profile_svc.resume_hash(RESUME), confirmed=True)
    postings = [
        _posting(
            external_id="1",
            title="Data Scientist",
            company="TinyAI",
            description="Python SQL PyTorch " * 50,
            description_is_snippet=False,
            company_size=30,
            posted_at=datetime.now().isoformat(),
        ),
        _posting(
            external_id="2",
            title="Senior Java Developer",
            company="BigCorp",
            location="Pune",
            country="in",
            description="Java Spring",
            url="https://adzuna/2",
        ),
    ]

    def fake_embed(texts):
        return [
            [1.0, 0.0] if ("Data Scientist" in t or "Target roles" in t) else [0.0, 1.0]
            for t in texts
        ]

    review_json = json.dumps(
        {
            "reviews": [
                {
                    "id": store._job_id(store.dedupe_key(postings[0])),
                    "fit": 90,
                    "reasons": ["PyTorch match"],
                    "german_required": "no",
                    "sponsorship": "yes",
                    "company_kind": "startup",
                },
            ]
        }
    )
    with (
        patch(
            "app.services.jobsearch.pipeline.available_sources",
            return_value={"adzuna": True, "apify": False},
        ),
        patch.object(AdzunaSource, "available", return_value=True),
        patch.object(AdzunaSource, "search", return_value=postings),
        patch.object(ApifyLinkedInSource, "available", return_value=False),
        patch("app.services.jobsearch.embeddings.embed_texts", side_effect=fake_embed),
        patch(
            "app.services.jobsearch.details.fetch_full_description", return_value=None
        ),
        patch(
            "app.services.jobsearch.pipeline.fetch_full_description", return_value=None
        ),
        patch(
            "app.services.generation.llm.generate_with_fallback",
            return_value=review_json,
        ),
    ):
        started = pipeline.start_search()
        run = _wait(started["search_id"])
        assert run["status"] == "done", run
        assert any("Apify" in n for n in run["notices"])  # skipped source is explained
        again = pipeline.start_search()
        assert again["cached"] is True and again["search_id"] == started["search_id"]

    jobs = store.get_jobs()
    assert [j["company"] for j in jobs] == ["TinyAI", "BigCorp"]  # best match first
    assert jobs[0]["review"]["fit"] == 90 and jobs[0]["score"] > jobs[1]["score"]


def test_search_refuses_without_confirmed_resume_or_sources():
    with pytest.raises(pipeline.SearchNotReady, match="resume"):
        pipeline.start_search()
    save_resume(RESUME, "h", confirmed=True)
    with pytest.raises(pipeline.SearchNotReady, match="profile"):
        pipeline.start_search()
    profile_svc.save(PROFILE, "h", confirmed=True)
    with (
        patch(
            "app.services.jobsearch.pipeline.available_sources",
            return_value={"adzuna": False, "apify": False},
        ),
        pytest.raises(pipeline.SearchNotReady, match="Adzuna or Apify"),
    ):
        pipeline.start_search()


def test_apify_runs_one_search_per_country_with_split_budget():
    from app.services.jobsearch.sources.apify import _budgets

    budgets = _budgets(["de", "in"], 100)
    assert budgets == {"de": 67, "in": 33}  # Germany (LinkedIn only) gets two shares
    item = {"id": "1", "title": "ML Engineer", "companyName": "X", "location": "Berlin"}
    with (
        patch(
            "app.services.jobsearch.sources.apify.get_apify_token", return_value="tok"
        ),
        patch(
            "app.services.jobsearch.sources.apify.requests.post",
            return_value=_resp(200, [item]),
        ) as post,
    ):
        out = ApifyLinkedInSource().search(
            SearchQuery(titles=["ML Engineer"], countries=["de", "in"]), max_results=100
        )
    assert post.call_count == 2  # one run per country
    urls = [c.kwargs["json"]["urls"][0] for c in post.call_args_list]
    assert "location=Germany" in urls[0] and "location=India" in urls[1]
    assert [c.kwargs["json"]["count"] for c in post.call_args_list] == [67, 33]
    assert [p.country for p in out] == [
        "de",
        "in",
    ]  # country known from the run, not guessed


def test_above_level_jobs_are_capped_and_explained():
    from app.services.jobsearch import ranking

    profile = SearchProfile(
        titles=["Data Scientist"], experience_levels=["entry"], years_experience=1.2
    )
    staff = {
        "id": "s",
        "title": "Staff Data Scientist",
        "description": "Python",
        "seniority": None,
        "country": "de",
        "company_size": None,
        "posted_at": None,
        "remote": None,
    }
    junior = {
        "id": "j",
        "title": "Junior Data Scientist",
        "description": "Python",
        "seniority": "Entry level",
        "country": "de",
        "company_size": None,
        "posted_at": None,
        "remote": None,
    }
    scored = {
        jid: (score, bd)
        for jid, score, bd in ranking.score_jobs(
            [staff, junior], None, profile, 30, 200
        )
    }
    assert scored["s"][0] <= ranking.ABOVE_SCORE_CAP
    assert scored["s"][1]["above_level"] == "a senior role for your level"
    assert (
        scored["j"][1]["above_level"] is None
        and scored["j"][0] > ranking.ABOVE_SCORE_CAP
    )


def test_years_asked_is_compared_with_the_users_years():
    from app.services.jobsearch import ranking

    profile = SearchProfile(
        titles=["Data Scientist"], experience_levels=["entry"], years_experience=1.2
    )
    asks5 = {
        "title": "Machine Learning Engineer",
        "seniority": None,
        "description": "5+ years of experience in Python",
    }
    asks2 = {
        "title": "Machine Learning Engineer",
        "seniority": None,
        "description": "2+ years of experience",
    }
    assert "5+" in (ranking.above_level(asks5, profile) or "")
    assert ranking.above_level(asks2, profile) is None
