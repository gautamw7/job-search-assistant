"""Deep generation module — small public interface.

Public seam:
  from app.services.generation import generate_outreach_message, regenerate_responses

Internal seams (not public):
  generation.llm, generation.store, generation.service
"""

from app.services.generation.llm import LLMError, get_fallback_models
from app.services.generation.service import (
    generate_followup,
    generate_outreach,
    generate_outreach_message,
    regenerate_responses,
)
from app.services.generation.store import (
    load_generated_messages,
    save_generated_messages,
)

__all__ = [
    "LLMError",
    "generate_followup",
    "generate_outreach",
    "generate_outreach_message",
    "get_fallback_models",
    "load_generated_messages",
    "regenerate_responses",
    "save_generated_messages",
]
