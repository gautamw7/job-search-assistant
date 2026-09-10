"""Compat shim - use app.infra.config instead."""
from app.infra.config import *
from app.infra.config import load_config

__all__ = ["load_config"]
