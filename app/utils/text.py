"""Compat shim - use app.infra.text instead."""
from app.infra.text import *
from app.infra.text import mask_key, truncate

__all__ = ["mask_key", "truncate"]
