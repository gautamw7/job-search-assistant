from services.helper import load_config
import os
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

def get_user_communication_prompt():
    """
    Get the user communication prompt and configuration.
    """
    path = ROOT_DIR / "prompts/user_communication.yaml"
    if not os.path.exists(path):
        raise FileNotFoundError(f"Prompt file not found: {path}")
    config = load_config(str(path))
    return config

def get_user_communication(config: dict) -> str:
    """Extracts and returns the user communication style from the config."""
    output_path = config.get('output_path', 'data/user_communication_style.json')
    if not os.path.isabs(output_path):
        output_path = ROOT_DIR / output_path
    else:
        output_path = Path(output_path)

    user_communication = ""

    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                user_communication = data.get("content", data.get("style", ""))
        except Exception as e:
            print(f"Error loading communication style JSON: {e}")

    if user_communication:
        print(f"Loaded user communication style from {output_path}.")
        return user_communication
    else:
        print(f"No user communication style found in {output_path}.")
        return config['default']
