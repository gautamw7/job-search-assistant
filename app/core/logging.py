"""Central logger with daily log rotation into logs/YYYY/MM/DD/.

Usage:
    from app.services.logger import get_logger
    logger = get_logger(__name__)
    logger.info("...")

Logs are written to:
    logs/YYYY/MM/DD/app.log   (all levels)
    logs/YYYY/MM/DD/error.log (ERROR+)
Plus console output.

The log directory is resolved relative to project root (one level above services/).
Multiple logs per day are stored in the same dated folder; TimedRotatingFileHandler
rotates at midnight with 14-day retention. Use LOG_LEVEL env to override.
"""

import logging
import logging.config
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

import yaml

from app.core.settings import find_project_root

_PROJECT_ROOT = find_project_root(Path(__file__).resolve())
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config" / "logging.yaml"
_CONFIGURED = False


def _get_log_dir() -> Path:
    """Return logs/YYYY/MM/DD path for today (local time)."""
    now = datetime.now()
    return (
        _PROJECT_ROOT
        / "logs"
        / f"{now.year:04d}"
        / f"{now.month:02d}"
        / f"{now.day:02d}"
    )


def _resolve_handlers_filenames(base_log_dir: Path) -> tuple[Path, Path]:
    app_log = base_log_dir / "app.log"
    err_log = base_log_dir / "error.log"
    app_log.parent.mkdir(parents=True, exist_ok=True)
    return app_log, err_log


def setup_logging(config_path: Path | str | None = None) -> None:
    """Configure logging from config/logging.yaml. Idempotent."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    cfg_path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    log_dir = _get_log_dir()
    app_log, err_log = _resolve_handlers_filenames(log_dir)

    # Default fallback if yaml missing
    if not cfg_path.exists():
        logging.basicConfig(
            level=logging.DEBUG
            if os.getenv("LOG_LEVEL", "").upper() == "DEBUG"
            else logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        _CONFIGURED = True
        logging.getLogger(__name__).warning(
            "logging.yaml not found at %s, using basicConfig", cfg_path
        )
        return

    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        # Override filenames to dated directory
        for handler_name in ("app_file", "error_file"):
            handler_cfg = cfg.get("handlers", {}).get(handler_name)
            if handler_cfg:
                # Keep only filename's basename, prepend dated dir
                # original: logs/app.log -> logs/YYYY/MM/DD/app.log
                if handler_name == "app_file":
                    handler_cfg["filename"] = str(app_log)
                elif handler_name == "error_file":
                    handler_cfg["filename"] = str(err_log)

        # Allow env override for level
        env_level = os.getenv("LOG_LEVEL", "").upper()
        if env_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            # Set root and job_search logger levels
            cfg.setdefault("root", {})["level"] = env_level
            if "job_search" in cfg.get("loggers", {}):
                cfg["loggers"]["job_search"]["level"] = env_level

        logging.config.dictConfig(cfg)
        _CONFIGURED = True
        logging.getLogger(__name__).info(
            "logging configured from %s -> app_log=%s error_log=%s",
            cfg_path,
            app_log,
            err_log,
        )
    except Exception as e:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        )
        _CONFIGURED = True
        logging.getLogger(__name__).exception(
            "failed to configure logging from %s: %s", cfg_path, e
        )


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger. Ensures logging is configured on first call.

    Args:
        name: Logger name, typically __name__. If None, returns root.
    """
    if not _CONFIGURED:
        setup_logging()
    return logging.getLogger(name if name else "job_search")


def get_log_dir() -> Path:
    """Public helper to get today's log directory (useful for tests/health)."""
    if not _CONFIGURED:
        setup_logging()
    return _get_log_dir()
