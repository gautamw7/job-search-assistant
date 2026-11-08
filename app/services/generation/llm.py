"""Internal: Gemini model fallback chain (single implementation)."""

import time

from google import genai
from google.genai import types

from app.core.logging import get_logger
from app.core.settings import MODEL_CONFIG
from app.infra.config import load_config
from app.services import usage
from app.services.secrets import get_gemini_key

logger = get_logger(__name__)

REQUEST_TIMEOUT_MS = 90_000
_FATAL_STATUS = {401, 403}  # a bad key will not get better on another model
_RATE_LIMITED = 429
RATE_LIMIT_WAITS_S = (2, 5, 10)  # free tier: brief waits before trying the next model


class LLMError(RuntimeError):
    """All configured models failed to produce a message."""


def get_fallback_models() -> list[str]:
    model_config = load_config(MODEL_CONFIG)
    models = (model_config.get("gemini") or {}).get("models", [])
    if not models:
        raise LLMError(f"No Gemini models configured in {MODEL_CONFIG}.")
    logger.debug("fallback models loaded count=%s models=%s", len(models), models)
    return models


def _client() -> genai.Client:
    """Build a client with the stored key, not whatever the environment holds."""
    http_options = types.HttpOptions(timeout=REQUEST_TIMEOUT_MS)
    api_key = get_gemini_key()
    if api_key:
        return genai.Client(api_key=api_key, http_options=http_options)
    return genai.Client(http_options=http_options)


def _int(value) -> int:
    return value if isinstance(value, int) else 0


def _record_usage(model: str, response, purpose: str) -> None:
    meta = getattr(response, "usage_metadata", None)
    usage.record_gemini(
        model,
        _int(getattr(meta, "prompt_token_count", 0)),
        _int(getattr(meta, "candidates_token_count", 0)),
        purpose,
    )


def generate_with_fallback(
    prompt: str,
    system_prompt: str | None = None,
    *,
    json_mode: bool = False,
    purpose: str = "outreach",
) -> str:
    usage.check_budget()
    client = _client()
    config_kwargs = {}
    if system_prompt:
        config_kwargs["system_instruction"] = system_prompt
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"
    config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
    last_error: Exception | None = None

    for model in get_fallback_models():
        try:
            logger.info(
                "trying model=%s purpose=%s prompt_len=%s", model, purpose, len(prompt)
            )
            kwargs = {"model": model, "contents": prompt}
            if config is not None:
                kwargs["config"] = config
            response = _call_with_rate_limit_retry(client, kwargs)
            _record_usage(model, response, purpose)
            text = getattr(response, "text", None)
            if isinstance(text, str) and text.strip():
                logger.info("model succeeded model=%s len=%s", model, len(text))
                return text
            logger.warning("model returned empty response model=%s", model)
            last_error = LLMError(f"{model} returned an empty response")
        except Exception as e:
            logger.warning("model %s failed", model, exc_info=True)
            last_error = e
            if getattr(e, "code", None) in _FATAL_STATUS:
                raise LLMError(
                    "Gemini rejected the API key. Check it in Settings."
                ) from e

    if is_rate_limit(last_error):
        raise LLMError(
            "Gemini free-tier limit reached. Try again in a minute, or add billing "
            "in Google AI Studio."
        ) from last_error
    raise LLMError(
        f"All Gemini models failed. Last error: {last_error}"
    ) from last_error


def _call_with_rate_limit_retry(client, kwargs):
    """Retry the same model briefly on 429 (free-tier rate limit) before giving up."""
    for wait in (*RATE_LIMIT_WAITS_S, None):
        try:
            return client.models.generate_content(**kwargs)
        except Exception as e:
            if getattr(e, "code", None) != _RATE_LIMITED or wait is None:
                raise
            logger.warning(
                "rate limited model=%s, retrying in %ss", kwargs["model"], wait
            )
            time.sleep(wait)
    raise AssertionError("unreachable")


def is_rate_limit(error: BaseException | None) -> bool:
    while error is not None:
        if getattr(error, "code", None) == _RATE_LIMITED:
            return True
        error = error.__cause__
    return False


def regenerate_with_fallback(prompt: str, system_prompt: str | None = None) -> str:
    return generate_with_fallback(prompt, system_prompt=system_prompt, purpose="refine")
