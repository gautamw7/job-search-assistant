"""Compat shim - use app.core.settings instead."""
from app.core.settings import *
from app.core.settings import (
    APP_DIR,
    CONFIG_DIR,
    DATA_DIR,
    DATA_DIR_ENV,
    ENRICH_DATA,
    GENERATED_MESSAGES,
    LOGGING_CONFIG,
    LOGS_DIR,
    MODEL_CONFIG,
    PROJECT_ROOT,
    PROMPTS_DIR,
    REPO_ROOT,
    RESUME_MD,
    RESUME_PDF,
    SECRETS_FILE,
    USER_COMM_STYLE,
    find_project_root,
)

__all__ = [
    "APP_DIR", "CONFIG_DIR", "DATA_DIR", "DATA_DIR_ENV", "ENRICH_DATA", "GENERATED_MESSAGES",
    "LOGGING_CONFIG", "LOGS_DIR", "MODEL_CONFIG", "PROJECT_ROOT", "PROMPTS_DIR",
    "REPO_ROOT", "RESUME_MD", "RESUME_PDF", "SECRETS_FILE", "USER_COMM_STYLE",
    "find_project_root",
]
