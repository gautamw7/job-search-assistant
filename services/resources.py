import os
from services.resume import check_resume_markdown, parse_resume_to_markdown, get_resume_markdown
from services.helper import load_config
from services.user_communication import get_user_communication

def build_resources(
    resume_path: str = "data/resume.pdf",
    style_path: str = "prompts/user_communication.yaml",
    prompt_config_path: str = "prompts/outreach_message.yaml"
) -> dict:
    """Builds and returns the resources needed for outreach message generation."""
    
    # 1. Extract Resume Markdown
    if check_resume_markdown():
        print("Markdown resume already exists. Loading existing Markdown.")
        user_resume_markdown = get_resume_markdown()
    else:
        print("Markdown resume not found. Parsing PDF to Markdown.")
        user_resume_markdown = parse_resume_to_markdown(resume_path)

    # 2. Load User Writing Style Guide
    user_communication_config = load_config(style_path)
    print(f"Loaded user communication style: {user_communication_config}")
    user_communication_style = get_user_communication(user_communication_config)

    # 3. Load Outreach Prompt Template Config
    if not os.path.exists(prompt_config_path):
        raise FileNotFoundError(f"Prompt config not found at {prompt_config_path}")

    prompt_config = load_config(prompt_config_path)
    system_prompt = prompt_config.get("system_prompt", "")
    template = prompt_config.get("user_prompt_template", "")

    # 4. Get default user_prefernces. 
    user_preferences_config = load_config("prompts/user_preferences.yaml") 

    return {
        "user_resume": user_resume_markdown,
        "user_communication_style": user_communication_style,
        "system_prompt": system_prompt,
        "template": template,
        "user_note": user_preferences_config['default'],
        "user_preferences": user_preferences_config['default']
    }
