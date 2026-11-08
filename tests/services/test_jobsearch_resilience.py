"""Regression: the live search failed with 'client has been closed' during embedding,
so nothing was scored. These tests use a client that closes itself on GC, like the real one."""

import weakref
from unittest.mock import MagicMock, patch

import pytest

from app.services.jobsearch import embeddings, ranking
from app.services.jobsearch.profile import SearchProfile


class _Session:
    """The HTTP session owned by a client; gone once the client is gone."""


class _Models:
    def __init__(self, session_ref):
        self._session_ref = session_ref  # weak: must not keep the session alive

    def embed_content(self, model, contents, config):
        if self._session_ref() is None:
            raise RuntimeError("Cannot send a request, as the client has been closed.")
        result = MagicMock()
        result.embeddings = [MagicMock(values=[0.1, 0.2, 0.3]) for _ in contents]
        return result


class _Client:
    def __init__(self):
        self.session = _Session()
        self.models = _Models(weakref.ref(self.session))


def test_old_pattern_loses_the_session_and_new_pattern_keeps_it():
    """Control: `_client().models.embed_content(...)` drops the client (and its
    session) before the request is sent; keeping the client in a variable does not."""
    with pytest.raises(RuntimeError, match="closed"):
        _Client().models.embed_content(model="m", contents=["x"], config=None)
    client = _Client()
    assert client.models.embed_content(model="m", contents=["x"], config=None)


def test_embedding_uses_a_client_that_outlives_the_request():
    with patch("app.services.generation.llm._client", side_effect=_Client):
        vectors = embeddings.embed_texts(["Data scientist at Acme\nPython SQL"])
    assert len(vectors) == 1 and len(vectors[0]) == 3


def test_pipeline_ranks_without_similarity_when_embeddings_fail():
    from app.services.jobsearch import pipeline
    from app.services.jobsearch.store import rows_for_ranking

    profile = SearchProfile(
        titles=["Data Scientist"], skills=["Python"], countries=["de"]
    )
    run = {"notices": []}
    jobs = [
        {
            "id": "a",
            "title": "Data Scientist",
            "description": "Python",
            "embedding": None,
            "embedding_model": None,
            "country": "de",
            "company_size": None,
            "posted_at": None,
            "seniority": None,
            "remote": None,
            "company": "X",
            "location": "Berlin",
        },
        {
            "id": "b",
            "title": "Java Developer",
            "description": "Java",
            "embedding": None,
            "embedding_model": None,
            "country": "de",
            "company_size": None,
            "posted_at": None,
            "seniority": None,
            "remote": None,
            "company": "Y",
            "location": "Berlin",
        },
    ]
    with patch.object(
        pipeline.embeddings, "embed_texts", side_effect=RuntimeError("closed")
    ):
        sims = pipeline._similarities(run, jobs, profile, "resume text")
    assert sims is None
    assert any("AI matching was unavailable" in n for n in run["notices"])
    assert rows_for_ranking([]) == []  # sanity: helper still importable

    scored = ranking.score_jobs(jobs, None, profile, 30, 200)
    by_id = {jid: score for jid, score, _ in scored}
    assert by_id["a"] > by_id["b"]  # the matching title still ranks first
    assert all(0 <= s <= 100 for s in by_id.values())
    weights_sum_breakdown = scored[0][2]
    assert weights_sum_breakdown["similarity"] is None
