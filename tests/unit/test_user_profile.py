"""Tests for UserProfile model and loader."""
import os
import pytest

from src.models.user_profile import UserProfile, load_profile, list_profiles, _parse_profile


SAMPLE_DATA = {
    "profile_name": "Backend Mumbai",
    "name": {"first": "Srini", "last": "Ravi"},
    "email": "srini@example.com",
    "phone": "+91-9876543210",
    "location": {
        "city": "Mumbai",
        "state": "Maharashtra",
        "country": "India",
        "zip": "400001",
    },
    "resume_path": "config/resumes/backend.pdf",
    "linkedin_url": "https://linkedin.com/in/srini",
    "github_url": "https://github.com/srini",
    "portfolio_url": "",
    "work_authorized": True,
    "sponsorship_required": False,
    "years_of_experience": 5,
    "current_company": "Acme Corp",
    "current_title": "SWE II",
    "notice_period_days": 30,
    "education": {
        "degree": "B.E.",
        "major": "Computer Science",
        "university": "Mumbai University",
        "graduation_year": 2020,
    },
    "preferred_roles": ["Software Engineer", "Backend Engineer"],
    "default_answers": {"gender": "Prefer not to say", "veteran_status": "No"},
}


class TestParseProfile:
    def test_parses_all_fields(self):
        p = _parse_profile(SAMPLE_DATA)
        assert p.profile_name == "Backend Mumbai"
        assert p.first_name == "Srini"
        assert p.last_name == "Ravi"
        assert p.email == "srini@example.com"
        assert p.phone == "+91-9876543210"
        assert p.city == "Mumbai"
        assert p.state == "Maharashtra"
        assert p.country == "India"
        assert p.zip_code == "400001"
        assert p.resume_path == "config/resumes/backend.pdf"
        assert p.linkedin_url == "https://linkedin.com/in/srini"
        assert p.years_of_experience == 5
        assert p.current_company == "Acme Corp"
        assert p.notice_period_days == 30
        assert p.degree == "B.E."
        assert p.major == "Computer Science"
        assert p.graduation_year == 2020
        assert p.preferred_roles == ["Software Engineer", "Backend Engineer"]
        assert p.default_answers["gender"] == "Prefer not to say"
        assert p.work_authorized is True
        assert p.sponsorship_required is False

    def test_defaults_for_missing_fields(self):
        p = _parse_profile({})
        assert p.profile_name == ""
        assert p.first_name == ""
        assert p.email == ""
        assert p.years_of_experience == 0
        assert p.preferred_roles == []
        assert p.default_answers == {}
        assert p.work_authorized is True
        assert p.notice_period_days == 30

    def test_handles_none_blocks(self):
        p = _parse_profile({"name": None, "location": None, "education": None})
        assert p.first_name == ""
        assert p.city == ""
        assert p.degree == ""


class TestUserProfileMethods:
    def test_summary_format(self):
        p = _parse_profile(SAMPLE_DATA)
        assert p.summary() == "Backend Mumbai (srini@example.com)"

    def test_to_dict_contains_all_fields(self):
        p = _parse_profile(SAMPLE_DATA)
        d = p.to_dict()
        assert d["profile_name"] == "Backend Mumbai"
        assert d["first_name"] == "Srini"
        assert d["email"] == "srini@example.com"
        assert d["preferred_roles"] == ["Software Engineer", "Backend Engineer"]
        assert d["default_answers"]["gender"] == "Prefer not to say"

    def test_to_dict_is_serializable(self):
        import json
        p = _parse_profile(SAMPLE_DATA)
        json.dumps(p.to_dict())  # should not raise


class TestLoadProfile:
    def test_loads_from_yaml_file(self, tmp_path):
        yaml_content = (
            "profile_name: Test\n"
            "name:\n  first: John\n  last: Doe\n"
            "email: john@doe.com\n"
            "phone: '+1-555-0000'\n"
            "location:\n  city: NYC\n  state: NY\n  country: USA\n  zip: '10001'\n"
            "resume_path: resume.pdf\n"
        )
        (tmp_path / "test_profile.yaml").write_text(yaml_content)
        p = load_profile("test_profile", profiles_dir=str(tmp_path))
        assert p.profile_name == "Test"
        assert p.first_name == "John"
        assert p.email == "john@doe.com"

    def test_raises_file_not_found_with_helpful_message(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="nonexistent"):
            load_profile("nonexistent", profiles_dir=str(tmp_path))

    def test_error_message_lists_available_profiles(self, tmp_path):
        (tmp_path / "other.yaml").write_text("profile_name: Other\n")
        with pytest.raises(FileNotFoundError, match="other"):
            load_profile("missing", profiles_dir=str(tmp_path))


class TestListProfiles:
    def test_returns_profiles_sorted(self, tmp_path):
        (tmp_path / "alpha.yaml").write_text(
            "profile_name: Alpha\nname:\n  first: A\n  last: B\nemail: a@b.com\n"
        )
        (tmp_path / "beta.yaml").write_text(
            "profile_name: Beta\nname:\n  first: C\n  last: D\nemail: c@d.com\n"
        )
        profiles = list_profiles(profiles_dir=str(tmp_path))
        assert len(profiles) == 2
        assert profiles[0][0] == "alpha"
        assert profiles[1][0] == "beta"
        assert "Alpha (a@b.com)" in profiles[0][1]

    def test_returns_empty_for_missing_directory(self, tmp_path):
        result = list_profiles(profiles_dir=str(tmp_path / "nonexistent"))
        assert result == []

    def test_handles_broken_yaml_gracefully(self, tmp_path):
        (tmp_path / "good.yaml").write_text(
            "profile_name: Good\nname:\n  first: G\n  last: H\nemail: g@h.com\n"
        )
        (tmp_path / "bad.yaml").write_text(":\n  invalid: yaml: : :")
        profiles = list_profiles(profiles_dir=str(tmp_path))
        names = [p[0] for p in profiles]
        assert "good" in names
        assert "bad" in names  # still listed, just with error message
