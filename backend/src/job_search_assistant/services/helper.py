import os

import yaml
from job_search_assistant.services.logger import get_logger

logger = get_logger(__name__)


def load_config(config_path: str) -> dict:
    """Loads and returns the configuration from a YAML file."""
    if not os.path.exists(config_path):
        logger.error("config file not found path=%s", config_path)
        raise FileNotFoundError(f"Config file not found at {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger.debug(
        "config loaded path=%s keys=%s",
        config_path,
        list(config.keys()) if isinstance(config, dict) else type(config).__name__,
    )
    return config
