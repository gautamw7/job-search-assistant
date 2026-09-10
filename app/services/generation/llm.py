"""Internal: LLM fallback chain + generation calls."""

from google import genai
from google.genai import types

from app.services.logger import get_logger
from app.services.paths import PROJECT_ROOT as ROOT_DIR
from app.utils.config import load_config

logger = get_logger(__name__)


def get_fallback_models() -> list[str]:
    primary = ROOT_DIR / "config" / "model_config.yaml"
    legacy = ROOT_DIR / "prompts" / "model_config.yaml"
    path = primary if primary.exists() else legacy
    if primary.exists() and legacy.exists():
        logger.debug("both config/model_config.yaml and prompts/model_config.yaml exist, using config/")
    elif not primary.exists() and legacy.exists():
        logger.warning("config/model_config.yaml not found, falling back to prompts/model_config.yaml")
    model_config = load_config(str(path))
    models = model_config.get("gemini", {}).get("models", [])
    logger.debug("fallback models loaded count=%s models=%s", len(models), models)
    return models


def generate_with_fallback(prompt: str, system_prompt: str | None = None) -> str:
    client = genai.Client()
    fallback = get_fallback_models()
    response = None
    for model in fallback:
        try:
            logger.info("trying model=%s prompt_len=%s", model, len(prompt))
            kwargs = {"model": model, "contents": prompt}
            if system_prompt:
                kwargs["config"] = types.GenerateContentConfig(system_instruction=system_prompt)
            response = client.models.generate_content(**kwargs)
            if response and response.text:
                logger.info("model succeeded model=%s len=%s", model, len(response.text))
                return response.text
            logger.warning("model returned empty response model=%s", model)
        except Exception:
            logger.warning("model %s failed", model, exc_info=True)
            continue
    if not response or not response.text:
        raise RuntimeError("Gemini model returned empty response or failed to generate message.")
    return response.text


def regenerate_with_fallback(prompt: str) -> str:
    client = genai.Client()
    fallback = get_fallback_models()
    response = None
    for model in fallback:
        try:
            logger.info("trying model=%s prompt_len=%s", model, len(prompt))
            response = client.models.generate_content(model=model, contents=prompt)
            if response and response.text:
                logger.info("model succeeded model=%s len=%s", model, len(response.text))
                return response.text
            logger.warning("model returned empty response model=%s", model)
        except Exception:
            logger.warning("model %s failed", model, exc_info=True)
            continue
    if not response or not response.text:
        raise RuntimeError("Gemini model returned empty response or failed during regeneration.")
    return response.text
