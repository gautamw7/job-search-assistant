"""Backward-compat shim — use app.utils.config instead."""

from app.utils.config import load_config

__all__ = ["load_config"]
