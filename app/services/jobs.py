"""Background generation jobs with real per-target progress and cancellation.

A job runs its targets on a small thread pool. The API starts a job and returns
immediately; the UI polls ``get_job`` for each target's stage
(queued -> enriching -> drafting -> checking -> success/failed/cancelled).
Cancelling stops targets that have not started yet; one already calling the LLM
is allowed to finish (its result is still saved to history).
"""

import threading
import time
import uuid
from collections import OrderedDict
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

from app.core.logging import get_logger
from app.services import usage
from app.services.generation import generate_outreach

logger = get_logger(__name__)

MAX_WORKERS = 3
MAX_RETAINED_JOBS = 50

_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="gen")
_jobs: "OrderedDict[str, _Job]" = OrderedDict()
_jobs_lock = threading.Lock()
_url_locks: dict[str, threading.Lock] = {}
_url_locks_guard = threading.Lock()


@contextmanager
def url_lock(url: str) -> Iterator[None]:
    """Serialise work per profile so one URL is never scraped/generated twice at once."""
    key = url.casefold()
    with _url_locks_guard:
        lock = _url_locks.setdefault(key, threading.Lock())
    with lock:
        yield


def dedupe_targets(targets: list[dict]) -> list[dict]:
    """Drop repeated URLs (case-insensitive), keeping input order."""
    seen: set[str] = set()
    unique = []
    for target in targets:
        key = target["linkedin_url"].casefold()
        if key not in seen:
            seen.add(key)
            unique.append(target)
    return unique


class _Job:
    def __init__(self, targets: list[dict]):
        self.id = uuid.uuid4().hex
        self.cancelled = False
        self.created = time.time()
        self.lock = threading.Lock()
        self.targets = [
            {
                "linkedin_url": t["linkedin_url"],
                "status": "queued",
                "generated_message": None,
                "generated_at": None,
                "error": None,
                "fact_check": None,
                "shared_background": [],
            }
            for t in targets
        ]

    def update(self, index: int, **fields) -> None:
        with self.lock:
            self.targets[index].update(fields)

    def snapshot(self) -> dict:
        with self.lock:
            targets = [dict(t) for t in self.targets]
        finished = {"success", "failed", "cancelled"}
        all_done = all(t["status"] in finished for t in targets)
        if all_done:
            status = "cancelled" if self.cancelled else "done"
        else:
            status = "running"
        return {
            "job_id": self.id,
            "status": status,
            "targets": targets,
            "usage": usage.scope_totals(self.id),
        }


def _run_target(job: _Job, index: int, target: dict) -> None:
    if job.cancelled:
        job.update(index, status="cancelled")
        return
    url = target["linkedin_url"]
    try:
        with url_lock(url), usage.usage_scope(job.id):
            record = generate_outreach(
                linkedin_url=url,
                user_note=target.get("additional_note"),
                user_preferences=target.get("additional_preferences"),
                refresh_profile=bool(target.get("refresh_profile")),
                on_stage=lambda stage: job.update(index, status=stage),
            )
        if not record.get("generated_message"):
            raise RuntimeError("Generation returned no content.")
        job.update(
            index,
            status="success",
            generated_message=record["generated_message"],
            generated_at=record.get("generated_at")
            or time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            fact_check=record.get("fact_check"),
            shared_background=record.get("shared_background") or [],
        )
    except Exception as e:
        logger.exception("job target failed url=%s", url)
        job.update(index, status="failed", error=str(e) or type(e).__name__)


def start_job(targets: list[dict]) -> str:
    targets = dedupe_targets(targets)
    job = _Job(targets)
    with _jobs_lock:
        _jobs[job.id] = job
        while len(_jobs) > MAX_RETAINED_JOBS:
            _jobs.popitem(last=False)
    for index, target in enumerate(targets):
        _executor.submit(_run_target, job, index, target)
    logger.info("job started id=%s targets=%s", job.id, len(targets))
    return job.id


def get_job(job_id: str) -> dict | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
    return job.snapshot() if job else None


def cancel_job(job_id: str) -> dict | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return None
    job.cancelled = True
    logger.info("job cancel requested id=%s", job_id)
    return job.snapshot()
