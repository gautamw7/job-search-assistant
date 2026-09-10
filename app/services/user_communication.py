import json
import os
from pathlib import Path

from app.services.helper import load_config
from app.services.logger import get_logger
from app.services.paths import PROJECT_ROOT as ROOT_DIR

logger = get_logger(__name__)


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
    output_path = config.get("output_path", "data/user_communication_style.json")
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
            logger.exception(
                "error loading communication style json path=%s err=%s", output_path, e
            )

    if user_communication:
        logger.info(
            "loaded user communication style path=%s len=%s",
            output_path,
            len(user_communication),
        )
        return user_communication
    else:
        logger.info(
            "no user communication style found path=%s, using default", output_path
        )
        return config["default"]
