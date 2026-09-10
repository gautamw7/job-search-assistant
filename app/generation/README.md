# app/generation - LLM generation domain

This folder co-locates prompts with code (industry standard: prompts next to service).
- prompts/ contains outreach_message.yaml, regeneration_prompt.yaml
- Future: llm.py, service.py will move here from app/services/generation/ for vertical slice.

For now, services/generation/ is canonical; this folder re-exports prompts for token-efficient imports.
