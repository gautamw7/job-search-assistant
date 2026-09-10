"""Backward-compat shim — use app.services.generation instead."""

from app.services.generation import (
    generate_outreach_message,
    get_fallback_models,
    load_generated_messages,
    regenerate_responses,
    save_generated_messages,
)

__all__ = [
    "generate_outreach_message",
    "get_fallback_models",
    "load_generated_messages",
    "regenerate_responses",
    "save_generated_messages",
]
