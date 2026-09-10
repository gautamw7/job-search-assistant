"""Compat shim - use app.infra.linkedin instead."""
from app.infra.linkedin import *
from app.infra.linkedin import LINKEDIN_PATTERN, extract_handle, normalize_url

__all__ = ["LINKEDIN_PATTERN", "extract_handle", "normalize_url"]
