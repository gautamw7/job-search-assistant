"""Internal: generate + regenerate orchestration."""

import time

from app.services.enrich import get_enrich_data
from app.services.generation.llm import regenerate_with_fallback
from app.services.generation.store import (
    load_generated_messages,
    save_generated_messages,
)
from app.services.logger import get_logger
from app.services.paths import PROMPTS_DIR
from app.services.resources import build_resources
from app.utils.config import load_config

logger = get_logger(__name__)


def regenerate_responses(
    linkedin_url: str,
    additional_note: str | None = None,
    additional_preferences: dict | None = None,
) -> dict:
    existing_messages = load_generated_messages()
    if linkedin_url not in existing_messages:
        raise ValueError(f"No history found for URL: {linkedin_url}")
    profile_data = existing_messages[linkedin_url]
    generations = profile_data.get("generations", [])
    if not generations:
        raise ValueError(f"No generations found for URL: {linkedin_url}")

    last_generation = generations[-1]
    last_generated_message = last_generation["generated_message"]
    current_preferences = (
        additional_preferences if additional_preferences is not None else last_generation.get("user_preferences", {})
    )

    user_resume = profile_data["context"]["user_resume"]
    user_communication_style = profile_data["context"]["user_communication_style"]

    regeneration_prompt_config = load_config(str(PROMPTS_DIR / "regeneration_prompt.yaml"))
    regeneration_prompt = regeneration_prompt_config["prompt"]
    preference_text = "\n".join(f"- {key}: {value}" for key, value in current_preferences.items())

    target_content = get_enrich_data(linkedin_url)

    filled_prompt = regeneration_prompt.format(
        target_content=target_content,
        user_resume=user_resume,
        user_communication_style=user_communication_style,
        last_generated_message=last_generated_message,
        additional_note=additional_note or "",
        preferences=preference_text,
    )
    logger.info("regenerating message url=%s prompt_len=%s", linkedin_url, len(filled_prompt))

    generated_message = regenerate_with_fallback(filled_prompt)
    generated_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    new_generation = {
        "user_note": additional_note,
        "user_preferences": current_preferences,
        "generated_message": generated_message,
        "generated_at": generated_at,
    }
    generations.append(new_generation)
    profile_data["generations"] = generations
    existing_messages[linkedin_url] = profile_data
    save_generated_messages(existing_messages)
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
    from app.services.generation.llm import generate_with_fallback

    resources = build_resources()
    user_resume = resources["user_resume"]
    user_communication_style = resources["user_communication_style"]
    system_prompt = resources["system_prompt"]
    template = resources["template"]
    pref = user_preferences if user_preferences is not None else resources["user_preferences"]
    note = user_note if user_note is not None else resources["user_note"]

    generated_messages = load_generated_messages()
    recipient_enrich_data = get_enrich_data(linkedin_url)

    context = {
        "user_resume": user_resume,
        "user_communication_style": user_communication_style,
        "system_prompt": system_prompt,
        "template": template,
        "recipient_enrich_data": recipient_enrich_data,
    }
    input_data = {**context, "user_preferences": pref, "user_notes": note}
    filled_prompt = template.format(**input_data)
    logger.info("generating outreach url=%s prompt_len=%s", linkedin_url, len(filled_prompt))

    generated_message = generate_with_fallback(filled_prompt, system_prompt=system_prompt)
    generated_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    if linkedin_url not in generated_messages:
        generated_messages[linkedin_url] = {"context": context, "generations": []}
    else:
        generated_messages[linkedin_url]["context"] = context
    generation = {
        "user_note": note,
        "user_preferences": pref,
        "generated_message": generated_message,
        "generated_at": generated_at,
    }
    generated_messages[linkedin_url]["generations"].append(generation)
    save_generated_messages(generated_messages)
    return generated_message
