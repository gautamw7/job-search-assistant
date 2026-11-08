"""Resume facts, years-required parsing, above-level rules, and what messages are written from."""

from datetime import date
from unittest.mock import patch

from app.services.jobsearch import profile as profile_svc
from app.services.jobsearch.facts import resume_facts, with_facts, years_required
from app.services.jobsearch.pipeline import above_level_terms
from app.services.jobsearch.profile import SearchProfile
from app.services.structured_resume import StructuredResume
from app.services.structured_resume import save as save_resume

# Shape of the real resume: a current internship, two earlier internships, one degree.
REAL = StructuredResume.model_validate(
    {
        "contact": {"name": "Alex"},
        "experience": [
            {
                "title": "AI/ML Intern",
                "company": "Autonex",
                "start": "Sep 2026",
                "end": "Present",
            },
            {
                "title": "Data Scientist Intern",
                "company": "Syngenta",
                "start": "Feb 2026",
                "end": "Jul 2026",
            },
            {
                "title": "Software Engineer Intern",
                "company": "Syngenta",
                "start": "Aug 2025",
                "end": "Jan 2026",
            },
        ],
        "education": [
            {
                "institution": "VIT",
                "degree": "Bachelor of Technology",
                "field": "CS",
                "start": "2022",
                "end": "2026",
            }
        ],
    }
)


def test_facts_describe_the_real_resume_without_guessing():
    f = resume_facts(REAL, today=date(2026, 11, 8))
    assert f.currently_employed and f.current_role == "AI/ML Intern at Autonex"
    assert f.degree_completed and f.highest_degree == "Bachelor of Technology CS"
    assert (
        f.years_experience == 1.2
    )  # 14 months, the overlapping Syngenta months counted once
    assert "Today's date: 2026-11-08" in f.as_prompt_text()


def test_overlapping_roles_are_not_double_counted():
    r = StructuredResume.model_validate(
        {
            "experience": [
                {"title": "A", "company": "X", "start": "Jan 2024", "end": "Dec 2024"},
                {"title": "B", "company": "Y", "start": "Jun 2024", "end": "Dec 2024"},
            ]
        }
    )
    assert resume_facts(r, today=date(2026, 1, 1)).years_experience == 1.0


def test_years_required_reads_ranges_as_their_lower_bound():
    assert years_required("Requires 5+ years of experience") == 5
    assert years_required("3-5 years of professional experience") == 3
    assert years_required("mindestens 3 Jahre Berufserfahrung") == 3
    assert years_required("at least 4 years experience") == 4
    assert years_required("Entry level, no experience needed") is None


def test_with_facts_fills_years_unless_the_user_set_them():
    base = SearchProfile(titles=["DS"])
    assert (
        with_facts(base, REAL).years_experience == resume_facts(REAL).years_experience
    )
    mine = SearchProfile(titles=["DS"], years_experience=2)
    assert with_facts(mine, REAL).years_experience == 2


def test_source_exclusion_only_when_the_user_does_not_want_senior_roles():
    entry = SearchProfile(titles=["DS"], experience_levels=["entry"])
    assert "senior" in (above_level_terms(entry) or "")
    open_to_senior = SearchProfile(titles=["DS"], experience_levels=["mid_senior"])
    assert above_level_terms(open_to_senior) is None
    off = SearchProfile(
        titles=["DS"], experience_levels=["entry"], hide_above_level=False
    )
    assert above_level_terms(off) is None


def test_profile_prompt_is_filled_with_the_facts():
    captured = {}

    def fake_generate(prompt, **kwargs):
        captured["prompt"] = prompt
        return '{"titles": ["Data Scientist"], "questions": []}'

    with patch(
        "app.services.generation.llm.generate_with_fallback", side_effect=fake_generate
    ):
        profile, _ = profile_svc.suggest(REAL)
    assert (
        "Today's date" in captured["prompt"]
        and "Currently employed: yes" in captured["prompt"]
    )
    assert "graduation" in captured["prompt"]  # the rule that stops asking about it
    assert profile.years_experience == 1.2


def test_messages_are_written_from_the_confirmed_structured_resume():
    from app.services import resources

    save_resume(REAL, "h", confirmed=True)
    with patch.object(resources, "load_config", return_value={"default": "x"}):
        text = resources._load_resume_markdown("/nonexistent.pdf")
    assert "AI/ML Intern" in text and "Autonex" in text


def test_vague_board_executive_label_does_not_override_the_title():
    from app.services.jobsearch import ranking

    profile = SearchProfile(
        titles=["Data Engineer"], experience_levels=["entry"], years_experience=1.2
    )
    sde = {
        "title": "SDE 1 - Data Engineer",
        "seniority": "Executive",
        "description": "",
    }
    assert ranking.above_level(sde, profile) is None
    real_director = {
        "title": "Director of Data",
        "seniority": "Executive",
        "description": "",
    }
    assert ranking.above_level(real_director, profile) is not None
