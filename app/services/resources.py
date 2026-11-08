import os

from app.core.logging import get_logger
from app.core.settings import PROMPTS_DIR, RESUME_MD, RESUME_PDF
from app.infra.config import load_config
from app.services.resume import (
    check_resume_markdown,
    convert_pdf_to_markdown,
    get_resume_markdown,
)
from app.services.user_communication import get_user_communication

logger = get_logger(__name__)


def format_preferences(preferences) -> str:
    """Render preferences identically everywhere (generate, regenerate, prompts).

    The configured default is free text; per-request preferences are a dict.
    """
    if not preferences:
        return ""
    if isinstance(preferences, dict):
        return "\n".join(f"- {k}: {v}" for k, v in preferences.items())
    return str(preferences).strip()


def _load_resume_markdown(resume_path: str) -> str:
    if check_resume_markdown():
        logger.info("markdown resume exists, loading")
        return get_resume_markdown()

    if not os.path.exists(resume_path):
        raise FileNotFoundError(
            "No resume found. Upload your resume in the Resume tab first."
        )
    logger.info("markdown resume not found, parsing pdf path=%s", resume_path)
    markdown = convert_pdf_to_markdown(resume_path)
    RESUME_MD.parent.mkdir(parents=True, exist_ok=True)
    RESUME_MD.write_text(markdown, encoding="utf-8")
    return markdown


def build_resources(
    resume_path: str | None = None,
    style_path: str | None = None,
    prompt_config_path: str | None = None,
) -> dict:
    """Builds and returns the resources needed for outreach message generation."""
    if resume_path is None:
        resume_path = str(RESUME_PDF)
    if style_path is None:
        style_path = str(PROMPTS_DIR / "user_communication.yaml")
    if prompt_config_path is None:
        prompt_config_path = str(PROMPTS_DIR / "outreach_message.yaml")

    # 1. Resume markdown
    user_resume_markdown = _load_resume_markdown(resume_path)

    # 2. User writing style guide
    user_communication_config = load_config(style_path)
    logger.debug(
        "user communication config loaded keys=%s",
        list(user_communication_config.keys()),
    )
    user_communication_style = get_user_communication(user_communication_config)

    # 3. Outreach prompt template
    if not os.path.exists(prompt_config_path):
        logger.error("prompt config not found path=%s", prompt_config_path)
        raise FileNotFoundError(f"Prompt config not found at {prompt_config_path}")

    prompt_config = load_config(prompt_config_path)
    system_prompt = prompt_config.get("system_prompt", "")
    template = prompt_config.get("user_prompt_template", "")
    default_note = prompt_config.get("default_user_note", "")
    logger.debug(
        "outreach prompt loaded system_prompt_len=%s template_len=%s",
        len(system_prompt),
        len(template),
    )

    # 4. Default message preferences
    user_preferences_config = load_config(str(PROMPTS_DIR / "user_preferences.yaml"))

    return {
        "user_resume": user_resume_markdown,
        "user_communication_style": user_communication_style,
        "system_prompt": system_prompt,
        "template": template,
        "user_note": default_note,
        "user_preferences": user_preferences_config["default"],
    }
