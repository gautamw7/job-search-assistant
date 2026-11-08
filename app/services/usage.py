"""Usage ledger, cost estimates, budget limits and user-editable app settings.

Every BrightData profile fetch and every Gemini call is recorded in the
``usage_events`` table (SQLite). Work running inside ``usage_scope(job_id)`` is also
totalled in memory so a job can report what *that run* consumed.

Prices are not hard-coded (they change); the user enters them in Settings. Until
they do, usage is assumed to be on the free tier: it costs $0.00 and is reported
with ``free_tier_assumed`` so the UI can say so. Count-based limits always work.
"""

import json
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime

from app.core.logging import get_logger
from app.core.settings import DATA_DIR
from app.infra.json_store import load_json, save_json

logger = get_logger(__name__)

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS: dict = {
    "pricing": {
        "brightdata_per_profile": None,
        "gemini_input_per_million": None,
        "gemini_output_per_million": None,
        "apify_per_result": None,
    },
    "budget": {
        "monthly_usd": None,
        "monthly_profiles": None,
        "monthly_apify_results": None,
    },
    "search": {
        "max_titles": 3,
        "max_days_old": 30,
        "adzuna_results_per_query": 50,
        "apify_results_per_search": 100,
        "startup_max_employees": 200,
    },
    "fact_check_enabled": True,
}

_scope: ContextVar[str | None] = ContextVar("usage_scope", default=None)
_scope_totals: dict[str, dict] = {}
_scope_lock = threading.Lock()


class BudgetExceededError(RuntimeError):
    """A configured monthly limit would be exceeded."""


def _settings_path():
    return DATA_DIR / SETTINGS_FILE


def _empty_totals() -> dict:
    return {
        "brightdata_profiles": 0,
        "gemini_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "embedding_calls": 0,
        "adzuna_calls": 0,
        "apify_results": 0,
    }


# ---- settings -------------------------------------------------------------------


def get_settings() -> dict:
    stored = load_json(_settings_path(), default={})
    stored = stored if isinstance(stored, dict) else {}
    merged = {
        "pricing": {**DEFAULT_SETTINGS["pricing"], **(stored.get("pricing") or {})},
        "budget": {**DEFAULT_SETTINGS["budget"], **(stored.get("budget") or {})},
        "search": {**DEFAULT_SETTINGS["search"], **(stored.get("search") or {})},
        "fact_check_enabled": stored.get(
            "fact_check_enabled", DEFAULT_SETTINGS["fact_check_enabled"]
        ),
    }
    return merged


def _clean_number(value):
    if value in (None, ""):
        return None
    number = float(value)
    if number < 0:
        raise ValueError("Prices and limits cannot be negative.")
    return number


def save_settings(patch: dict) -> dict:
    current = get_settings()
    for section in ("pricing", "budget", "search"):
        for key, value in (patch.get(section) or {}).items():
            if key not in current[section]:
                raise ValueError(f"Unknown setting {section}.{key}")
            current[section][key] = _clean_number(value)
    if "fact_check_enabled" in patch:
        current["fact_check_enabled"] = bool(patch["fact_check_enabled"])
    save_json(_settings_path(), current)
    return current


# ---- recording ------------------------------------------------------------------


@contextmanager
def usage_scope(name: str):
    """Attribute usage recorded in this context (this thread) to ``name``."""
    token = _scope.set(name)
    try:
        yield
    finally:
        _scope.reset(token)


def _add(totals: dict, event: dict) -> None:
    kind = event["kind"]
    if kind == "brightdata":
        totals["brightdata_profiles"] += event.get("profiles", 0)
    elif kind == "gemini":
        totals["gemini_calls"] += 1
        totals["input_tokens"] += event.get("input_tokens", 0)
        totals["output_tokens"] += event.get("output_tokens", 0)
    elif kind == "embedding":
        totals["embedding_calls"] += 1
    elif kind == "adzuna":
        totals["adzuna_calls"] += event.get("calls", 1)
    elif kind == "apify":
        totals["apify_results"] += event.get("results", 0)


def _record(event: dict) -> None:
    event["ts"] = datetime.now().isoformat(timespec="seconds")
    scope = _scope.get()
    if scope:
        event["scope"] = scope
        with _scope_lock:
            _add(_scope_totals.setdefault(scope, _empty_totals()), event)
    try:
        from app.infra.db import connect

        with connect() as conn:
            conn.execute(
                "INSERT INTO usage_events (ts, kind, scope, data) VALUES (?, ?, ?, ?)",
                (event["ts"], event["kind"], event.get("scope"), json.dumps(event)),
            )
    except Exception:  # usage tracking must never break generation
        logger.exception("failed to record usage event=%s", event)


def record_brightdata(profiles: int) -> None:
    if profiles > 0:
        _record({"kind": "brightdata", "profiles": int(profiles)})


def record_embedding(model: str, texts: int) -> None:
    _record({"kind": "embedding", "model": model, "texts": int(texts)})


def record_adzuna(calls: int = 1) -> None:
    _record({"kind": "adzuna", "calls": int(calls)})


def record_apify(results: int) -> None:
    _record({"kind": "apify", "results": int(results)})


def record_gemini(
    model: str, input_tokens: int, output_tokens: int, purpose: str
) -> None:
    _record(
        {
            "kind": "gemini",
            "model": model,
            "purpose": purpose,
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
        }
    )


# ---- reporting ------------------------------------------------------------------


def _cost_parts(totals: dict, pricing: dict) -> tuple[float, bool]:
    """(USD cost, whether a used service had no price and was assumed free)."""
    assumed = False

    def price(key: str) -> float:
        nonlocal assumed
        value = pricing.get(key)
        if value is None:
            assumed = True
            return 0.0
        return value

    cost = 0.0
    if totals.get("brightdata_profiles"):
        cost += totals["brightdata_profiles"] * price("brightdata_per_profile")
    if totals.get("gemini_calls"):
        cost += totals["input_tokens"] / 1e6 * price("gemini_input_per_million")
        cost += totals["output_tokens"] / 1e6 * price("gemini_output_per_million")
    if totals.get("apify_results"):
        cost += totals["apify_results"] * price("apify_per_result")
    # Adzuna and Gemini embeddings are free on their standard tiers.
    return round(cost, 4), assumed


def estimate_cost(totals: dict, pricing: dict) -> float:
    """Estimated USD; services without a configured price are assumed free."""
    return _cost_parts(totals, pricing)[0]


def _with_cost(totals: dict, pricing: dict) -> dict:
    cost, assumed = _cost_parts(totals, pricing)
    return {**totals, "estimated_cost": cost, "free_tier_assumed": assumed}


def _totals_since(prefix: str) -> dict:
    """Totals for events whose timestamp starts with ``prefix`` (a month or a day)."""
    from app.infra.db import connect
    from app.services.legacy_import import absorb_legacy_json

    absorb_legacy_json("usage")
    totals = _empty_totals()
    with connect() as conn:
        rows = conn.execute(
            "SELECT data FROM usage_events WHERE ts LIKE ? || '%'", (prefix,)
        ).fetchall()
    for row in rows:
        _add(totals, json.loads(row["data"]))
    return totals


def scope_totals(name: str) -> dict:
    with _scope_lock:
        totals = dict(_scope_totals.get(name) or _empty_totals())
    return _with_cost(totals, get_settings()["pricing"])


def summary() -> dict:
    settings = get_settings()
    now = datetime.now()
    month = _with_cost(_totals_since(now.strftime("%Y-%m")), settings["pricing"])
    today = _with_cost(_totals_since(now.strftime("%Y-%m-%d")), settings["pricing"])
    pricing = settings["pricing"]
    return {
        "month": {"period": now.strftime("%Y-%m"), **month},
        "today": today,
        "settings": settings,
        "pricing_configured": all(v is not None for v in pricing.values()),
        "unpriced_services": [k for k, v in pricing.items() if v is None],
    }


def check_budget(profiles: int = 0, apify_results: int = 0) -> None:
    """Raise before spending if this would break a monthly limit."""
    settings = get_settings()
    budget = settings["budget"]
    if all(v is None for v in budget.values()):
        return
    month = _totals_since(datetime.now().strftime("%Y-%m"))
    apify_limit = budget.get("monthly_apify_results")
    if apify_limit is not None and month["apify_results"] + apify_results > apify_limit:
        raise BudgetExceededError(
            f"Monthly Apify limit reached ({int(apify_limit)} job results). "
            "Raise it in Settings → Usage & budget."
        )
    limit = budget["monthly_profiles"]
    if limit is not None and month["brightdata_profiles"] + profiles > limit:
        raise BudgetExceededError(
            f"Monthly profile limit reached ({int(limit)} profiles). "
            "Raise it in Settings → Usage & budget."
        )
    usd = budget["monthly_usd"]
    if usd is not None:
        # Unpriced services count as $0 (free tier assumed).
        cost = estimate_cost(month, settings["pricing"])
        if cost >= usd:
            raise BudgetExceededError(
                f"Monthly budget of ${usd:g} reached (estimated ${cost:.2f} spent). "
                "Raise it in Settings → Usage & budget."
            )
