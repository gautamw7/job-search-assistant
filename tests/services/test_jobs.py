import threading
import time

from app.services import jobs


def _wait(job_id, timeout=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = jobs.get_job(job_id)
        if state["status"] != "running":
            return state
        time.sleep(0.02)
    raise AssertionError("job did not finish")


def test_job_dedupes_keeps_order_and_isolates_failures(monkeypatch):
    def fake(linkedin_url, on_stage=None, **_):
        on_stage("drafting")
        if "bad" in linkedin_url:
            raise RuntimeError("boom")
        return {
            "generated_message": f"msg for {linkedin_url}",
            "generated_at": "2026-11-08 10:00:00",
            "fact_check": {"status": "pass", "issues": []},
            "shared_background": ["Both of you studied at X."],
        }

    monkeypatch.setattr(jobs, "generate_outreach", fake)
    urls = [
        "https://www.linkedin.com/in/a",
        "https://www.linkedin.com/in/bad",
        "https://www.linkedin.com/in/A",  # duplicate of the first (case-insensitive)
        "https://www.linkedin.com/in/c",
    ]
    state = _wait(jobs.start_job([{"linkedin_url": u} for u in urls]))

    assert [t["linkedin_url"] for t in state["targets"]] == [urls[0], urls[1], urls[3]]
    assert [t["status"] for t in state["targets"]] == ["success", "failed", "success"]
    assert state["targets"][1]["error"] == "boom"
    assert state["targets"][0]["fact_check"]["status"] == "pass"
    assert state["targets"][0]["shared_background"] == ["Both of you studied at X."]
    assert "gemini_calls" in state["usage"]
    assert state["status"] == "done"


def test_cancel_stops_targets_that_have_not_started(monkeypatch):
    gate = threading.Event()

    def slow(linkedin_url, on_stage=None, **_):
        gate.wait(5)
        return {"generated_message": "ok"}

    monkeypatch.setattr(jobs, "generate_outreach", slow)
    targets = [{"linkedin_url": f"https://www.linkedin.com/in/p{i}"} for i in range(8)]
    job_id = jobs.start_job(targets)
    jobs.cancel_job(job_id)
    gate.set()
    state = _wait(job_id)

    statuses = [t["status"] for t in state["targets"]]
    assert "cancelled" in statuses
    assert state["status"] == "cancelled"
