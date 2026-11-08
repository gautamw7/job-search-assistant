"""Usage ledger, cost estimates, budget limits and user-editable app settings.

Every BrightData profile fetch and every Gemini call is recorded in
``DATA_DIR/usage.json``. Work running inside ``usage_scope(job_id)`` is also
totalled in memory so a job can report what *that run* consumed.

Prices are not hard-coded (they change); the user enters them in Settings. Until
they do, costs show as unknown but count-based limits (profiles per month) still
work.
"""

import threading
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime

from app.core.logging import get_logger
from app.core.settings import DATA_DIR
from app.infra.json_store import load_json, save_json, update_json

logger = get_logger(__name__)

LEDGER_FILE = "usage.json"
SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS: dict = {
    "pricing": {
        "brightdata_per_profile": None,
        "gemini_input_per_million": None,
        "gemini_output_per_million": None,
    },
    "budget": {"monthly_usd": None, "monthly_profiles": None},
    "fact_check_enabled": True,
}

_scope: ContextVar[str | None] = ContextVar("usage_scope", default=None)
_scope_totals: dict[str, dict] = {}
_scope_lock = threading.Lock()


class BudgetExceededError(RuntimeError):
    """A configured monthly limit would be exceeded."""


def _ledger_path():
    return DATA_DIR / LEDGER_FILE


def _settings_path():
    return DATA_DIR / SETTINGS_FILE


def _empty_totals() -> dict:
    return {
        "brightdata_profiles": 0,
        "gemini_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
    }


# ---- settings -------------------------------------------------------------------


def get_settings() -> dict:
    stored = load_json(_settings_path(), default={})
    stored = stored if isinstance(stored, dict) else {}
    merged = {
        "pricing": {**DEFAULT_SETTINGS["pricing"], **(stored.get("pricing") or {})},
        "budget": {**DEFAULT_SETTINGS["budget"], **(stored.get("budget") or {})},
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
    for section in ("pricing", "budget"):
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
    if event["kind"] == "brightdata":
        totals["brightdata_profiles"] += event.get("profiles", 0)
    else:
        totals["gemini_calls"] += 1
        totals["input_tokens"] += event.get("input_tokens", 0)
        totals["output_tokens"] += event.get("output_tokens", 0)


def _record(event: dict) -> None:
    event["ts"] = datetime.now().isoformat(timespec="seconds")
    scope = _scope.get()
    if scope:
        event["scope"] = scope
        with _scope_lock:
            _add(_scope_totals.setdefault(scope, _empty_totals()), event)
    try:
        update_json(
            _ledger_path(),
            lambda d: d.setdefault("events", []).append(event),
            default={"events": []},
        )
    except Exception:  # usage tracking must never break generation
        logger.exception("failed to record usage event=%s", event)


def record_brightdata(profiles: int) -> None:
    if profiles > 0:
        _record({"kind": "brightdata", "profiles": int(profiles)})


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


def estimate_cost(totals: dict, pricing: dict) -> float | None:
    """Estimated USD, or None if a price needed for the usage is not configured."""
    cost = 0.0
    if totals["brightdata_profiles"]:
        if pricing.get("brightdata_per_profile") is None:
            return None
        cost += totals["brightdata_profiles"] * pricing["brightdata_per_profile"]
    if totals["gemini_calls"]:
        pin = pricing.get("gemini_input_per_million")
        pout = pricing.get("gemini_output_per_million")
        if pin is None or pout is None:
            return None
        cost += (
            totals["input_tokens"] / 1e6 * pin + totals["output_tokens"] / 1e6 * pout
        )
    return round(cost, 4)


def _with_cost(totals: dict, pricing: dict) -> dict:
    return {**totals, "estimated_cost": estimate_cost(totals, pricing)}


def _events() -> list[dict]:
    data = load_json(_ledger_path(), default={"events": []})
    events = data.get("events", []) if isinstance(data, dict) else []
    return [e for e in events if isinstance(e, dict) and "kind" in e]


def _totals_since(prefix: str) -> dict:
    totals = _empty_totals()
    for event in _events():
        if str(event.get("ts", "")).startswith(prefix):
            _add(totals, event)
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
    }


def check_budget(profiles: int = 0) -> None:
    """Raise before spending if this would break a monthly limit."""
    settings = get_settings()
    budget = settings["budget"]
    if budget["monthly_profiles"] is None and budget["monthly_usd"] is None:
        return
    month = _totals_since(datetime.now().strftime("%Y-%m"))
    limit = budget["monthly_profiles"]
    if limit is not None and month["brightdata_profiles"] + profiles > limit:
        raise BudgetExceededError(
            f"Monthly profile limit reached ({int(limit)} profiles). "
            "Raise it in Settings → Usage & budget."
        )
    usd = budget["monthly_usd"]
    if usd is not None:
        cost = estimate_cost(month, settings["pricing"])
        if cost is None:
            logger.warning(
                "monthly USD budget set but prices are missing; not enforced"
            )
        elif cost >= usd:
            raise BudgetExceededError(
                f"Monthly budget of ${usd:g} reached (estimated ${cost:.2f} spent). "
                "Raise it in Settings → Usage & budget."
            )
