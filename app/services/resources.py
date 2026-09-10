import os

from app.services.helper import load_config
from app.services.logger import get_logger
from app.services.paths import PROJECT_ROOT, PROMPTS_DIR
from app.services.resume import (
    check_resume_markdown,
    get_resume_markdown,
    parse_resume_to_markdown,
)
from app.services.user_communication import get_user_communication

logger = get_logger(__name__)


def build_resources(
    resume_path: str | None = None,
    style_path: str | None = None,
    prompt_config_path: str | None = None,
) -> dict:
    """Builds and returns the resources needed for outreach message generation."""
    # Resolve defaults to absolute paths via PROJECT_ROOT / PROMPTS_DIR
    if resume_path is None:
        resume_path = str(PROJECT_ROOT / "data" / "resume.pdf")
    if style_path is None:
        style_path = str(PROMPTS_DIR / "user_communication.yaml")
    if prompt_config_path is None:
        prompt_config_path = str(PROMPTS_DIR / "outreach_message.yaml")

    # 1. Extract Resume Markdown
    if check_resume_markdown():
        logger.info("markdown resume exists, loading")
        user_resume_markdown = get_resume_markdown()
    else:
        logger.info("markdown resume not found, parsing pdf path=%s", resume_path)
        user_resume_markdown = parse_resume_to_markdown(resume_path)

    # 2. Load User Writing Style Guide
    user_communication_config = load_config(style_path)
    logger.debug(
        "user communication config loaded keys=%s",
        list(user_communication_config.keys()),
    )
    user_communication_style = get_user_communication(user_communication_config)

    # 3. Load Outreach Prompt Template Config
    if not os.path.exists(prompt_config_path):
        logger.error("prompt config not found path=%s", prompt_config_path)
        raise FileNotFoundError(f"Prompt config not found at {prompt_config_path}")

    prompt_config = load_config(prompt_config_path)
    system_prompt = prompt_config.get("system_prompt", "")
    template = prompt_config.get("user_prompt_template", "")
    logger.debug(
        "outreach prompt loaded system_prompt_len=%s template_len=%s",
        len(system_prompt),
        len(template),
    )

    # 4. Get default user_prefernces.
    user_preferences_config = load_config(str(PROMPTS_DIR / "user_preferences.yaml"))
    logger.debug("user preferences config loaded")

    return {
        "user_resume": user_resume_markdown,
        "user_communication_style": user_communication_style,
        "system_prompt": system_prompt,
        "template": template,
        "user_note": user_preferences_config["default"],
        "user_preferences": user_preferences_config["default"],
    }
