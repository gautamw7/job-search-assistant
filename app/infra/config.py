"""YAML config loader — replaces services.helper.load_config."""

from pathlib import Path

import yaml

from app.core.logging import get_logger

logger = get_logger(__name__)


def load_config(config_path: str | Path) -> dict:
    config_path = Path(config_path)
    if not config_path.exists():
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
