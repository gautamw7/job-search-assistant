def url_normalize(linkedin_url: str) -> str:
    """
    Normalizes a LinkedIn URL by stripping whitespace and converting it to lowercase.

    Args:
        linkedin_url: The LinkedIn URL to be normalized.
    """
    return linkedin_url.strip().lower()
