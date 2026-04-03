"""UserProfile model and multi-profile loader."""
import os
from dataclasses import dataclass, field
from glob import glob
from typing import Optional

import yaml


@dataclass
class UserProfile:
    # Identity
    profile_id: str
    profile_name: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: str
    # Location
    city: str
    state: str
    country: str
    zip_code: str
    # Links
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    # Employment summary
    years_of_experience: int = 0
    notice_period_days: int = 0
    # Work history (list of {company, title, from, to, currently_working_here})
    experience: list[dict] = field(default_factory=list)
    # Education (list of {degree, major, university, graduation_year})
    education: list[dict] = field(default_factory=list)
    # Preferences
    target_roles: list[str] = field(default_factory=list)
    target_locations: list[str] = field(default_factory=list)
    # Documents
    resume_file_name: str = ""
    resume_path_hint: str = ""
    # Catch-all for ATS-specific answers
    custom_answers: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        """One-line summary: 'Backend Mumbai (srini@example.com)'"""
        return f"{self.profile_name} ({self.email})"

    def to_dict(self) -> dict:
        """For JSON serialization."""
        return {
            "profile_id": self.profile_id,
            "profile_name": self.profile_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "zip_code": self.zip_code,
            "linkedin_url": self.linkedin_url,
            "github_url": self.github_url,
            "portfolio_url": self.portfolio_url,
            "years_of_experience": self.years_of_experience,
            "notice_period_days": self.notice_period_days,
            "experience": list(self.experience),
            "education": list(self.education),
            "target_roles": list(self.target_roles),
            "target_locations": list(self.target_locations),
            "resume_file_name": self.resume_file_name,
            "resume_path_hint": self.resume_path_hint,
            "custom_answers": dict(self.custom_answers),
        }


def _profiles_dir() -> str:
    """Return absolute path to config/profiles/ relative to project root."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config", "profiles",
    )


def load_profile(name: str, profiles_dir: Optional[str] = None) -> "UserProfile":
    """Load UserProfile from config/profiles/{name}.yaml.

    Raises FileNotFoundError with a helpful message if the file is missing.
    """
    base = profiles_dir or _profiles_dir()
    path = os.path.join(base, f"{name}.yaml")
    if not os.path.exists(path):
        available = []
        if os.path.exists(base):
            available = [
                os.path.splitext(f)[0]
                for f in os.listdir(base)
                if f.endswith(".yaml")
            ]
        raise FileNotFoundError(
            f"Profile '{name}' not found at {path}. "
            f"Available: {available or 'none (create config/profiles/{name}.yaml)'}"
        )
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return _parse_profile(data)


def list_profiles(profiles_dir: Optional[str] = None) -> list[tuple[str, str]]:
    """Return [(name, summary), ...] for all profiles in config/profiles/."""
    base = profiles_dir or _profiles_dir()
    if not os.path.exists(base):
        return []
    result = []
    for path in sorted(glob(os.path.join(base, "*.yaml"))):
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            profile = _parse_profile(data)
            result.append((name, profile.summary()))
        except Exception as e:
            result.append((name, f"(failed to load: {e})"))
    return result


def _parse_profile(data: dict) -> "UserProfile":
    """Parse raw YAML dict into UserProfile, with defaults for missing fields."""
    location_block = data.get("location") or {}
    links_block = data.get("links") or {}
    employment_block = data.get("employment") or {}
    work_prefs_block = data.get("work_preferences") or {}
    documents_block = data.get("documents") or {}

    return UserProfile(
        profile_id=data.get("profile_id", ""),
        profile_name=data.get("profile_name", ""),
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
        full_name=data.get("full_name", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        city=location_block.get("city", ""),
        state=location_block.get("state", ""),
        country=location_block.get("country", ""),
        zip_code=str(location_block.get("zip_code", "")),
        linkedin_url=links_block.get("linkedin_url", ""),
        github_url=links_block.get("github_url", ""),
        portfolio_url=links_block.get("portfolio_url", ""),
        years_of_experience=int(employment_block.get("years_of_experience", 0)),
        notice_period_days=int(employment_block.get("notice_period_days", 0)),
        experience=list(data.get("experience") or []),
        education=list(data.get("education") or []),
        target_roles=list(work_prefs_block.get("target_roles") or []),
        target_locations=list(work_prefs_block.get("target_locations") or []),
        resume_file_name=documents_block.get("resume_file_name", ""),
        resume_path_hint=documents_block.get("resume_path_hint", ""),
        custom_answers=dict(data.get("custom_answers") or {}),
    )
