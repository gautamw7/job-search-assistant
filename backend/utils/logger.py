import inspect
import logging
import logging.config
from datetime import datetime, timezone
from pathlib import Path

from backend.utils.config import load_config


def setup_logging() -> None:
    """Set up logging configuration based on the loaded config."""
    config = load_config("backend/config/logging.yaml")

    project_root = Path(config.get("project_root", "."))

    now = datetime.now(timezone.utc)

    log_dir = project_root / "logs" / str(now.year) / now.strftime("%B") / str(now.day)

    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"logs_{now.strftime('%H-%M-%S')}_UTC.log"

    config["handlers"]["file"]["filename"] = str(log_file)

    logging.config.dictConfig(config)

    logging.getLogger(__name__).info(
        "Logging initialized: %s",
        log_file,
    )


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return a logger for the calling module.

    If no name is provided, automatically use the caller's module name.
    """
    if not logging.getLogger().handlers:
        setup_logging()

    if name is None:
        frame = inspect.currentframe()
        caller_frame = frame.f_back if frame else None

        if caller_frame:
            name = caller_frame.f_globals.get("__name__", "__main__")
        else:
            name = "__main__"

    return logging.getLogger(name)


if __name__ == "__main__":
    setup_logging()

    logger = get_logger()

    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
