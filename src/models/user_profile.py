"""UserProfile model and multi-profile loader."""
import os
from dataclasses import dataclass, field
from glob import glob
from typing import Optional

import yaml


@dataclass
class UserProfile:
    profile_name: str
    first_name: str
    last_name: str
    email: str
    phone: str
    city: str
    state: str
    country: str
    zip_code: str
    resume_path: str
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    work_authorized: bool = True
    sponsorship_required: bool = False
    years_of_experience: int = 0
    current_company: str = ""
    current_title: str = ""
    notice_period_days: int = 30
    degree: str = ""
    major: str = ""
    university: str = ""
    graduation_year: int = 0
    preferred_roles: list[str] = field(default_factory=list)
    default_answers: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        """One-line summary: 'Backend Mumbai (srini@example.com)'"""
        return f"{self.profile_name} ({self.email})"

    def to_dict(self) -> dict:
        """For JSON serialization."""
        return {
            "profile_name": self.profile_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "zip_code": self.zip_code,
            "resume_path": self.resume_path,
            "linkedin_url": self.linkedin_url,
            "github_url": self.github_url,
            "portfolio_url": self.portfolio_url,
            "work_authorized": self.work_authorized,
            "sponsorship_required": self.sponsorship_required,
            "years_of_experience": self.years_of_experience,
            "current_company": self.current_company,
            "current_title": self.current_title,
            "notice_period_days": self.notice_period_days,
            "degree": self.degree,
            "major": self.major,
            "university": self.university,
            "graduation_year": self.graduation_year,
            "preferred_roles": list(self.preferred_roles),
            "default_answers": dict(self.default_answers),
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
    name_block = data.get("name") or {}
    location_block = data.get("location") or {}
    education_block = data.get("education") or {}
    return UserProfile(
        profile_name=data.get("profile_name", ""),
        first_name=name_block.get("first", ""),
        last_name=name_block.get("last", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        city=location_block.get("city", ""),
        state=location_block.get("state", ""),
        country=location_block.get("country", ""),
        zip_code=str(location_block.get("zip", "")),
        resume_path=data.get("resume_path", ""),
        linkedin_url=data.get("linkedin_url", ""),
        github_url=data.get("github_url", ""),
        portfolio_url=data.get("portfolio_url", ""),
        work_authorized=bool(data.get("work_authorized", True)),
        sponsorship_required=bool(data.get("sponsorship_required", False)),
        years_of_experience=int(data.get("years_of_experience", 0)),
        current_company=data.get("current_company", ""),
        current_title=data.get("current_title", ""),
        notice_period_days=int(data.get("notice_period_days", 30)),
        degree=education_block.get("degree", ""),
        major=education_block.get("major", ""),
        university=education_block.get("university", ""),
        graduation_year=int(education_block.get("graduation_year", 0)),
        preferred_roles=list(data.get("preferred_roles") or []),
        default_answers=dict(data.get("default_answers") or {}),
    )
