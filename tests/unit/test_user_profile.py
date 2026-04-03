"""Tests for UserProfile model and loader."""
import os
import pytest

from src.models.user_profile import UserProfile, load_profile, list_profiles, _parse_profile


SAMPLE_DATA = {
    "profile_id": "backend_mumbai",
    "profile_name": "Backend Mumbai",
    "first_name": "Srinivas",
    "last_name": "Ravi",
    "full_name": "Srinivas Ravi",
    "email": "srinivasravi404@gmail.com",
    "phone": "+917208816364",
    "location": {
        "city": "Mumbai",
        "state": "Maharashtra",
        "country": "India",
        "zip_code": "400706",
    },
    "links": {
        "linkedin_url": "https://linkedin.com/in/srinivas-ravi",
        "github_url": "https://github.com/SrinivasRavi",
        "portfolio_url": "",
    },
    "employment": {
        "years_of_experience": 7,
        "notice_period_days": 0,
    },
    "experience": [
        {
            "company": "Salesforce Inc",
            "title": "Senior Member of Technical Staff",
            "from": "29/04/2022",
            "to": "21/08/2024",
            "currently_working_here": False,
        },
        {
            "company": "Amazon Inc.",
            "title": "Software Development Engineer",
            "from": "19/08/2019",
            "to": "21/04/2022",
            "currently_working_here": False,
        },
    ],
    "education": [
        {
            "degree": "MS",
            "major": "Computer Science",
            "university": "University at Buffalo",
            "graduation_year": 2019,
        },
        {
            "degree": "BE",
            "major": "Computer Engineering",
            "university": "Mumbai University",
            "graduation_year": 2015,
        },
    ],
    "work_preferences": {
        "target_roles": ["Backend Engineer", "Software Engineer", "Java Developer"],
        "target_locations": ["Mumbai"],
    },
    "documents": {
        "resume_file_name": "backend_resume.pdf",
        "resume_path_hint": "/path/to/backend_resume.pdf",
    },
    "custom_answers": {
        "sponsorship_required": "No",
        "authorized_to_work": "Yes",
        "current_ctc": "",
        "expected_ctc": "30 LPA",
        "gender": "Prefer not to say",
        "veteran_status": "No",
    },
}


class TestParseProfile:
    def test_parses_all_fields(self):
        p = _parse_profile(SAMPLE_DATA)
        assert p.profile_id == "backend_mumbai"
        assert p.profile_name == "Backend Mumbai"
        assert p.first_name == "Srinivas"
        assert p.last_name == "Ravi"
        assert p.full_name == "Srinivas Ravi"
        assert p.email == "srinivasravi404@gmail.com"
        assert p.phone == "+917208816364"

    def test_parses_location(self):
        p = _parse_profile(SAMPLE_DATA)
        assert p.city == "Mumbai"
        assert p.state == "Maharashtra"
        assert p.country == "India"
        assert p.zip_code == "400706"

    def test_parses_links(self):
        p = _parse_profile(SAMPLE_DATA)
        assert p.linkedin_url == "https://linkedin.com/in/srinivas-ravi"
        assert p.github_url == "https://github.com/SrinivasRavi"
        assert p.portfolio_url == ""

    def test_parses_employment(self):
        p = _parse_profile(SAMPLE_DATA)
        assert p.years_of_experience == 7
        assert p.notice_period_days == 0

    def test_parses_experience_list(self):
        p = _parse_profile(SAMPLE_DATA)
        assert len(p.experience) == 2
        assert p.experience[0]["company"] == "Salesforce Inc"
        assert p.experience[0]["title"] == "Senior Member of Technical Staff"
        assert p.experience[1]["company"] == "Amazon Inc."

    def test_parses_education_list(self):
        p = _parse_profile(SAMPLE_DATA)
        assert len(p.education) == 2
        assert p.education[0]["degree"] == "MS"
        assert p.education[0]["university"] == "University at Buffalo"
        assert p.education[1]["degree"] == "BE"

    def test_parses_work_preferences(self):
        p = _parse_profile(SAMPLE_DATA)
        assert p.target_roles == ["Backend Engineer", "Software Engineer", "Java Developer"]
        assert p.target_locations == ["Mumbai"]

    def test_parses_documents(self):
        p = _parse_profile(SAMPLE_DATA)
        assert p.resume_file_name == "backend_resume.pdf"
        assert p.resume_path_hint == "/path/to/backend_resume.pdf"

    def test_parses_custom_answers(self):
        p = _parse_profile(SAMPLE_DATA)
        assert p.custom_answers["sponsorship_required"] == "No"
        assert p.custom_answers["authorized_to_work"] == "Yes"
        assert p.custom_answers["expected_ctc"] == "30 LPA"
        assert p.custom_answers["gender"] == "Prefer not to say"

    def test_defaults_for_missing_fields(self):
        p = _parse_profile({})
        assert p.profile_id == ""
        assert p.profile_name == ""
        assert p.first_name == ""
        assert p.full_name == ""
        assert p.email == ""
        assert p.years_of_experience == 0
        assert p.notice_period_days == 0
        assert p.experience == []
        assert p.education == []
        assert p.target_roles == []
        assert p.target_locations == []
        assert p.custom_answers == {}
        assert p.resume_path_hint == ""

    def test_handles_none_blocks(self):
        p = _parse_profile({
            "location": None,
            "links": None,
            "employment": None,
            "work_preferences": None,
            "documents": None,
        })
        assert p.city == ""
        assert p.linkedin_url == ""
        assert p.years_of_experience == 0
        assert p.target_roles == []
        assert p.resume_path_hint == ""


class TestUserProfileMethods:
    def test_summary_format(self):
        p = _parse_profile(SAMPLE_DATA)
        assert p.summary() == "Backend Mumbai (srinivasravi404@gmail.com)"

    def test_to_dict_contains_all_fields(self):
        p = _parse_profile(SAMPLE_DATA)
        d = p.to_dict()
        assert d["profile_id"] == "backend_mumbai"
        assert d["profile_name"] == "Backend Mumbai"
        assert d["first_name"] == "Srinivas"
        assert d["full_name"] == "Srinivas Ravi"
        assert d["email"] == "srinivasravi404@gmail.com"
        assert d["target_roles"] == ["Backend Engineer", "Software Engineer", "Java Developer"]
        assert d["custom_answers"]["gender"] == "Prefer not to say"
        assert d["resume_path_hint"] == "/path/to/backend_resume.pdf"

    def test_to_dict_education_is_list(self):
        p = _parse_profile(SAMPLE_DATA)
        d = p.to_dict()
        assert isinstance(d["education"], list)
        assert len(d["education"]) == 2

    def test_to_dict_experience_is_list(self):
        p = _parse_profile(SAMPLE_DATA)
        d = p.to_dict()
        assert isinstance(d["experience"], list)
        assert len(d["experience"]) == 2

    def test_to_dict_is_serializable(self):
        import json
        p = _parse_profile(SAMPLE_DATA)
        json.dumps(p.to_dict())  # should not raise


class TestLoadProfile:
    def test_loads_from_yaml_file(self, tmp_path):
        yaml_content = (
            "profile_id: test_profile\n"
            "profile_name: Test\n"
            "first_name: John\n"
            "last_name: Doe\n"
            "full_name: John Doe\n"
            "email: john@doe.com\n"
            "phone: '+1-555-0000'\n"
            "location:\n  city: NYC\n  state: NY\n  country: USA\n  zip_code: '10001'\n"
        )
        (tmp_path / "test_profile.yaml").write_text(yaml_content)
        p = load_profile("test_profile", profiles_dir=str(tmp_path))
        assert p.profile_id == "test_profile"
        assert p.profile_name == "Test"
        assert p.first_name == "John"
        assert p.email == "john@doe.com"
        assert p.zip_code == "10001"

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
            "profile_id: alpha\nprofile_name: Alpha\n"
            "first_name: A\nlast_name: B\nfull_name: A B\nemail: a@b.com\n"
            "phone: ''\nlocation:\n  city: ''\n  state: ''\n  country: ''\n  zip_code: ''\n"
        )
        (tmp_path / "beta.yaml").write_text(
            "profile_id: beta\nprofile_name: Beta\n"
            "first_name: C\nlast_name: D\nfull_name: C D\nemail: c@d.com\n"
            "phone: ''\nlocation:\n  city: ''\n  state: ''\n  country: ''\n  zip_code: ''\n"
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
            "profile_id: good\nprofile_name: Good\n"
            "first_name: G\nlast_name: H\nfull_name: G H\nemail: g@h.com\n"
            "phone: ''\nlocation:\n  city: ''\n  state: ''\n  country: ''\n  zip_code: ''\n"
        )
        (tmp_path / "bad.yaml").write_text(":\n  invalid: yaml: : :")
        profiles = list_profiles(profiles_dir=str(tmp_path))
        names = [p[0] for p in profiles]
        assert "good" in names
        assert "bad" in names  # still listed, just with error message
