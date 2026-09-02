import json
import time
from pathlib import Path

from google import genai
from google.genai import types
from job_search_assistant.services.enrich import get_enrich_data
from job_search_assistant.services.helper import load_config
from job_search_assistant.services.logger import get_logger
from job_search_assistant.services.paths import GENERATED_MESSAGES as OUTPUT_PATH
from job_search_assistant.services.paths import PROJECT_ROOT as ROOT_DIR
from job_search_assistant.services.resources import build_resources

logger = get_logger(__name__)


def get_fallback_models() -> list[str]:
    """
    Retrieve fallback model names from the model configuration YAML file.

    Returns:
        list[str]: List of fallback model names.
    """
    # Primary location is config/model_config.yaml, fallback to prompts/ for backward compat
    primary = ROOT_DIR / "config" / "model_config.yaml"
    legacy = ROOT_DIR / "prompts" / "model_config.yaml"
    path = primary if primary.exists() else legacy
    if primary.exists() and legacy.exists():
        logger.debug(
            "both config/model_config.yaml and prompts/model_config.yaml exist, using config/"
        )
    elif not primary.exists() and legacy.exists():
        logger.warning(
            "config/model_config.yaml not found, falling back to prompts/model_config.yaml"
        )
    model_config = load_config(str(path))
    models = model_config.get("gemini", {}).get("models", [])
    logger.debug("fallback models loaded count=%s models=%s", len(models), models)
    return models


def save_generated_messages(
    messages: dict,
    output_path: Path | str = OUTPUT_PATH,
) -> None:
    """
    Save generated messages dictionary to a JSON file.

    Args:
        messages (dict): Dictionary mapping LinkedIn URLs to context and generation history.
        output_path (Path | str): File system path to persist JSON output.
    """
    output_path = Path(output_path)
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            messages,
            f,
            ensure_ascii=False,
            indent=4,
        )

    logger.info(
        "generated messages saved path=%s entries=%s", output_path, len(messages)
    )


def load_generated_messages(
    output_path: Path | str = OUTPUT_PATH,
) -> dict:
    """
    Load generated messages dictionary from a JSON file.

    Args:
        output_path (Path | str): File system path from which to read JSON data.

    Returns:
        dict: Deserialized generated messages data, or empty dict if file does not exist.
    """
    output_path = Path(output_path)
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.debug(
            "loaded generated messages path=%s entries=%s", output_path, len(data)
        )
        return data

    except FileNotFoundError:
        logger.info("generated messages file not found path=%s", output_path)
        return {}
    except Exception as e:
        logger.exception(
            "failed to load generated messages path=%s err=%s", output_path, e
        )
        return {}


def regenerate_responses(
    linkedin_url: str,
    additional_note: str | None = None,
    additional_preferences: dict | None = None,
) -> dict:
    """
    Regenerate the latest outreach message for a given LinkedIn profile using updated preferences/notes.

    Args:
        linkedin_url (str): Target LinkedIn profile URL.
        additional_note (str | None): New user instructions or context for revision.
        additional_preferences (dict | None): Revised message style/tone preferences.

    Returns:
        dict: Dictionary containing linkedin_url, generated_message, and timestamp.

    Raises:
        ValueError: If no prior generation history or profile exists for the URL.
        RuntimeError: If model generation fails or returns empty response.
    """

    # ---------------------------------------------------------
    # 1. Load existing data
    # ---------------------------------------------------------

    existing_messages = load_generated_messages()

    if linkedin_url not in existing_messages:
        raise ValueError(f"No history found for URL: {linkedin_url}")

    profile_data = existing_messages[linkedin_url]

    generations = profile_data.get("generations", [])

    if not generations:
        raise ValueError(f"No generations found for URL: {linkedin_url}")

    # ---------------------------------------------------------
    # 2. Get latest generation
    # ---------------------------------------------------------

    last_generation = generations[-1]

    last_generated_message = last_generation["generated_message"]

    # Use previous preferences if new preferences weren't provided
    current_preferences = (
        additional_preferences
        if additional_preferences is not None
        else last_generation.get("user_preferences", {})
    )

    # ---------------------------------------------------------
    # 2.5 Get latest generation
    # ---------------------------------------------------------

    user_resume = profile_data["context"]["user_resume"]
    user_communication_style = profile_data["context"]["user_communication_style"]

    # ---------------------------------------------------------
    # 3. Load regeneration prompt
    # ---------------------------------------------------------

    from job_search_assistant.services.paths import PROMPTS_DIR

    regeneration_prompt_config = load_config(
        str(PROMPTS_DIR / "regeneration_prompt.yaml")
    )

    regeneration_prompt = regeneration_prompt_config["prompt"]

    # Convert preferences dict into readable prompt text
    preference_text = "\n".join(
        f"- {key}: {value}" for key, value in current_preferences.items()
    )

    # ---------------------------------------------------------
    # 4. Build regeneration prompt
    # ---------------------------------------------------------

    filled_prompt = regeneration_prompt.format(
        user_resume=user_resume,
        user_communication_style=user_communication_style,
        last_generated_message=last_generated_message,
        additional_note=additional_note or "",
        preferences=preference_text,
    )

    logger.info(
        "regenerating message url=%s prompt_len=%s", linkedin_url, len(filled_prompt)
    )
    logger.debug(
        "regeneration prompt url=%s prompt=%.2000s", linkedin_url, filled_prompt
    )

    # ---------------------------------------------------------
    # 5. Generate revised message (Model failure bubbles up)
    # ---------------------------------------------------------

    logger.info(
        "regen generating via fallback models count=%s url=%s",
        len(get_fallback_models()),
        linkedin_url,
    )
    client = genai.Client()
    fallback_model = get_fallback_models()
    response = None
    try:
        for model in fallback_model:
            try:
                logger.info("trying model=%s url=%s", model, linkedin_url)
                response = client.models.generate_content(
                    model=model,
                    contents=filled_prompt,
                )
                if response and response.text:
                    logger.info(
                        "model succeeded model=%s url=%s len=%s",
                        model,
                        linkedin_url,
                        len(response.text),
                    )
                    break  # Successful generation, exit loop
                logger.warning(
                    "model returned empty response model=%s url=%s", model, linkedin_url
                )
            except Exception as e:
                logger.warning(
                    "model %s failed url=%s err=%s",
                    model,
                    linkedin_url,
                    e,
                    exc_info=True,
                )
                continue  # Try next model
    except Exception as e:
        logger.exception(
            "gemini model failure during regeneration url=%s err=%s", linkedin_url, e
        )
        raise RuntimeError(
            f"Gemini API model failure during regeneration: {e!s}"
        ) from e

    if not response or not response.text:
        logger.error(
            "gemini returned empty response during regeneration url=%s", linkedin_url
        )
        raise RuntimeError(
            "Gemini model returned empty response or failed during regeneration."
        )

    generated_message = response.text

    # ---------------------------------------------------------
    # 6. Store new generation
    # ---------------------------------------------------------

    generated_at = time.strftime(
        "%Y-%m-%d %H:%M:%S",
        time.localtime(),
    )

    new_generation = {
        "user_note": additional_note,
        "user_preferences": current_preferences,
        "generated_message": generated_message,
        "generated_at": generated_at,
    }

    generations.append(new_generation)

    profile_data["generations"] = generations

    existing_messages[linkedin_url] = profile_data
    logger.info(
        "regen stored new generation url=%s total_generations=%s",
        linkedin_url,
        len(generations),
    )

    # ---------------------------------------------------------
    # 7. Save
    # ---------------------------------------------------------

    save_generated_messages(existing_messages)

    # ---------------------------------------------------------
    # 8. API response
    # ---------------------------------------------------------

    return {
        "linkedin_url": linkedin_url,
        "generated_message": generated_message,
        "generated_at": generated_at,
    }


def generate_outreach_message(
    linkedin_url: str,
    user_note: str | None = None,
    user_preferences: dict | None = None,
) -> str:
    """
    Generate an outreach message for a single target LinkedIn profile.

    Fetches enrichment data for the URL, formats prompt with resume/preferences,
    invokes Gemini to generate message content, updates history in data/generated_messages.json,
    and returns the generated message string.

    Args:
        linkedin_url (str): Target LinkedIn profile URL.
        user_note (str | None): Optional target-specific note or instruction.
        user_preferences (dict | None): Optional style/tone preferences override.

    Returns:
        str: The generated outreach message text.
    """

    # ---------------------------------------------------------
    # 1. Initialize Gemini client
    # ---------------------------------------------------------

    client = genai.Client()

    # ---------------------------------------------------------
    # 2. Build resources
    # ---------------------------------------------------------

    resources = build_resources()

    user_resume = resources["user_resume"]
    user_communication_style = resources["user_communication_style"]
    system_prompt = resources["system_prompt"]
    template = resources["template"]

    pref = (
        user_preferences
        if user_preferences is not None
        else resources["user_preferences"]
    )
    note = user_note if user_note is not None else resources["user_note"]

    # ---------------------------------------------------------
    # 3. Load existing database
    # ---------------------------------------------------------

    generated_messages = load_generated_messages()

    # ---------------------------------------------------------
    # 4. Get LinkedIn enrichment data
    # ---------------------------------------------------------

    recipient_enrich_data = get_enrich_data(linkedin_url)

    # ---------------------------------------------------------
    # 5. Build context & prompt
    # ---------------------------------------------------------

    context = {
        "user_resume": user_resume,
        "user_communication_style": user_communication_style,
        "system_prompt": system_prompt,
        "template": template,
        "recipient_enrich_data": recipient_enrich_data,
    }

    input_data = {
        **context,
        "user_preferences": pref,
        "user_notes": note,
    }

    filled_prompt = template.format(**input_data)

    logger.info(
        "generating outreach url=%s prompt_len=%s template_len=%s",
        linkedin_url,
        len(filled_prompt),
        len(template),
    )
    logger.debug("outreach prompt url=%s prompt=%.2000s", linkedin_url, filled_prompt)

    # ---------------------------------------------------------
    # 6. Generate message content via Gemini
    # ---------------------------------------------------------

    fallback_model = get_fallback_models()
    logger.info(
        "outreach generating via fallback models count=%s url=%s",
        len(fallback_model),
        linkedin_url,
    )

    response = None
    try:
        for model in fallback_model:
            try:
                logger.info("trying model=%s url=%s", model, linkedin_url)
                response = client.models.generate_content(
                    model=model,
                    contents=filled_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                    ),
                )
                if response and response.text:
                    logger.info(
                        "model succeeded model=%s url=%s len=%s",
                        model,
                        linkedin_url,
                        len(response.text),
                    )
                    break  # Successful generation, exit loop
                logger.warning(
                    "model returned empty response model=%s url=%s", model, linkedin_url
                )
            except Exception as e:
                logger.warning(
                    "model %s failed url=%s err=%s",
                    model,
                    linkedin_url,
                    e,
                    exc_info=True,
                )
                continue  # Try next model
    except Exception as e:
        logger.exception(
            "gemini model failure during generation url=%s err=%s", linkedin_url, e
        )
        raise RuntimeError(f"Gemini API model failure during generation: {e!s}") from e

    if not response or not response.text:
        logger.error("gemini returned empty response url=%s", linkedin_url)
        raise RuntimeError(
            "Gemini model returned empty response or failed to generate message."
        )

    generated_message = response.text
    generated_at = time.strftime(
        "%Y-%m-%d %H:%M:%S",
        time.localtime(),
    )
    logger.info(
        "outreach generated url=%s len=%s", linkedin_url, len(generated_message)
    )

    # ---------------------------------------------------------
    # 7. Store generation record
    # ---------------------------------------------------------

    if linkedin_url not in generated_messages:
        generated_messages[linkedin_url] = {
            "context": context,
            "generations": [],
        }
        logger.info("new context created url=%s", linkedin_url)
    else:
        generated_messages[linkedin_url]["context"] = context
        logger.debug("context updated url=%s", linkedin_url)

    generation = {
        "user_note": note,
        "user_preferences": pref,
        "generated_message": generated_message,
        "generated_at": generated_at,
    }

    generated_messages[linkedin_url]["generations"].append(generation)
    logger.info(
        "stored generation url=%s total=%s",
        linkedin_url,
        len(generated_messages[linkedin_url]["generations"]),
    )

    # ---------------------------------------------------------
    # 8. Persist to disk
    # ---------------------------------------------------------

    save_generated_messages(generated_messages)

    return generated_message
