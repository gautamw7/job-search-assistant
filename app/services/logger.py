"""Compat shim - use app.core.logging instead."""
from app.core.logging import *
from app.core.logging import get_log_dir, get_logger, setup_logging

__all__ = ["get_log_dir", "get_logger", "setup_logging"]
