from collections import defaultdict
from google import genai
from google.genai import types

import time
import json
from pathlib import Path

from services.enrich import get_enrich_data
from services.resources import build_resources
from services.helper import load_config

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT_DIR / "data" / "generated_messages.json"


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

    print(f"Generated messages saved to {output_path}")


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
            return json.load(f)

    except FileNotFoundError:
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
    # 3. Load regeneration prompt
    # ---------------------------------------------------------

    regeneration_prompt_config = load_config("prompts/regeneration_prompt.yaml")

    regeneration_prompt = regeneration_prompt_config["prompt"]

    # Convert preferences dict into readable prompt text
    preference_text = "\n".join(
        f"- {key}: {value}"
        for key, value in current_preferences.items()
    )

    # ---------------------------------------------------------
    # 4. Build regeneration prompt
    # ---------------------------------------------------------

    filled_prompt = regeneration_prompt.format(
        last_generated_message=last_generated_message,
        additional_note=additional_note or "",
        preferences=preference_text,
    )

    print(
        f"Regenerating message for {linkedin_url}:\n"
        f"{filled_prompt}\n"
    )

    # ---------------------------------------------------------
    # 5. Generate revised message (Model failure bubbles up)
    # ---------------------------------------------------------

    client = genai.Client()

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=filled_prompt,
        )
    except Exception as e:
        raise RuntimeError(f"Gemini API model failure during regeneration: {str(e)}") from e

    if not response or not response.text:
        raise RuntimeError("Gemini model returned empty response or failed during regeneration.")

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

    pref = user_preferences if user_preferences is not None else resources["user_preferences"]
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

    print(
        f"Generating outreach message for {linkedin_url}:\n"
        f"{filled_prompt}\n"
    )

    # ---------------------------------------------------------
    # 6. Generate message content via Gemini
    # ---------------------------------------------------------

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=filled_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )
    except Exception as e:
        raise RuntimeError(f"Gemini API model failure during generation: {str(e)}") from e

    if not response or not response.text:
        raise RuntimeError("Gemini model returned empty response or failed to generate message.")

    generated_message = response.text
    generated_at = time.strftime(
        "%Y-%m-%d %H:%M:%S",
        time.localtime(),
    )

    # ---------------------------------------------------------
    # 7. Store generation record
    # ---------------------------------------------------------

    if linkedin_url not in generated_messages:
        generated_messages[linkedin_url] = {
            "context": context,
            "generations": [],
        }
    else:
        generated_messages[linkedin_url]["context"] = context

    generation = {
        "user_note": note,
        "user_preferences": pref,
        "generated_message": generated_message,
        "generated_at": generated_at,
    }

    generated_messages[linkedin_url]["generations"].append(generation)

    # ---------------------------------------------------------
    # 8. Persist to disk
    # ---------------------------------------------------------

    save_generated_messages(generated_messages)

    return generated_message
