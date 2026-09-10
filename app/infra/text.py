"""Text helpers — masking, truncation, formatting."""


def mask_key(key: str) -> str:
    if len(key) <= 8:
        return "********"
    return key[:4] + "********" + key[-4:]


def truncate(text: str, max_len: int = 200, suffix: str = "...") -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix
