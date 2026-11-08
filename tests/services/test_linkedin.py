import pytest

from app.infra.linkedin import is_linkedin_profile_url, normalize_url

CANON = "https://www.linkedin.com/in/jane-doe"


@pytest.mark.parametrize(
    "raw",
    [
        CANON,
        CANON + "/",
        "http://www.linkedin.com/in/jane-doe",
        "https://linkedin.com/in/jane-doe/",
        "https://in.linkedin.com/in/jane-doe?utm_source=share",
        "linkedin.com/in/jane-doe",
        "  " + CANON + "#about  ",
    ],
)
def test_variants_normalize_to_one_key(raw):
    assert is_linkedin_profile_url(raw)
    assert normalize_url(raw) == CANON


@pytest.mark.parametrize(
    "raw",
    ["https://github.com/jane-doe", "not a url", "https://www.linkedin.com/company/x"],
)
def test_non_profiles_rejected(raw):
    assert not is_linkedin_profile_url(raw)
