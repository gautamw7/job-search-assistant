from backend.utils.logger import get_logger
from backend.database.repository.outreach_messages import get_latest_outreach_message
from backend.workflows.processing import build_resources
from backend.utils.helper import load_config

logger = get_logger(__name__)


def prompt_format(prompt_template: str, input_data: dict) -> str:
    """
    Format the prompt template with the provided input data.
    """
    try:
        missing_keys = [
            key for key in input_data.keys() if f"{{{key}}}" not in prompt_template
        ]
        if missing_keys:
            logger.warning("Missing keys in prompt template: %s", missing_keys)
            raise KeyError(f"Missing keys in prompt template: {missing_keys}")

        logger.info("Formatting prompt with provided input data.")
        formatted_prompt = prompt_template.format(**input_data)
        return formatted_prompt
    except KeyError:
        raise
    except Exception as e:
        logger.error("Error formatting prompt: %s", e)
        raise RuntimeError(f"Error formatting prompt: {e}")


def orchestrate_prompt_generation(
    linkedin_url: str, user_note: str, message_personalization: dict
) -> dict:
    """
    Generate a prompt based on the provided LinkedIn URL and user note.
    Returns a dictionary containing user_prompt and system_prompt, or raises an exception.
    """
    logger.info("Generating prompt for LinkedIn URL: %s", linkedin_url)
    input_data = build_resources(linkedin_url, user_note, message_personalization)

    prompt_template = load_config("backend/prompts/outreach.yaml")
    if not prompt_template:
        logger.error("Outreach prompt template not found in configuration.")
        raise FileNotFoundError("Outreach prompt template not found in configuration.")

    user_prompt = prompt_format(
        prompt_template.get("user_prompt_template", ""), input_data
    )

    return {
        "user_prompt": user_prompt,
        "system_prompt": prompt_template.get("system_prompt", ""),
    }


def orchestrate_regeneration_prompt(
    linkedin_url: str, user_note: str, message_personalization: dict
) -> dict:
    """
    Orchestrate the regeneration of content based on the provided prompt and user note.
    """
    logger.info("Orchestrating regeneration prompt for LinkedIn URL: %s", linkedin_url)
    try:
        latest_content = get_latest_outreach_message(linkedin_url)
        logger.info("Latest content found for LinkedIn URL: %s", linkedin_url)

        regeneration_config = load_config("backend/prompts/regenerate_outreach.yaml")
        prompt_template = regeneration_config.get("prompt_template", None)

        if not prompt_template:
            logger.error("Prompt template not found in regeneration configuration.")
            raise FileNotFoundError(
                "Prompt template not found in regeneration configuration."
            )

        inputs = {
            "previous_message": latest_content.get("generated_text", ""),
            "user_note": user_note,
            "message_personalization": message_personalization,
        }

        # Format the regeneration prompt template
        user_prompt = prompt_format(prompt_template, inputs)

        # Get the default outreach prompt for the system prompt instructions
        outreach_config = load_config("backend/prompts/outreach.yaml")

        return {
            "user_prompt": user_prompt,
            "system_prompt": outreach_config.get("system_prompt", ""),
        }

    except LookupError:
        logger.info("No prior outreach message found. Generating from scratch.")
        return orchestrate_prompt_generation(
            linkedin_url=linkedin_url,
            user_note=user_note,
            message_personalization=message_personalization,
        )
    except Exception as e:
        logger.error("Error orchestrating regeneration prompt: %s", e)
        raise RuntimeError(f"Error orchestrating regeneration prompt: {e}")
