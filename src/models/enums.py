"""Status enums and reason codes for the job search pipeline."""
from enum import Enum


class ApplicationStatus(str, Enum):
    NOT_APPLIED = "NOT_APPLIED"
    APPLIED = "APPLIED"
    APPLY_FAILED = "APPLY_FAILED"
    HEARD_BACK = "HEARD_BACK"
    REJECTED = "REJECTED"


class SourceType(str, Enum):
    CAREER_PAGE = "CAREER_PAGE"
    API = "API"
    EXTERNAL_SCRAPER = "EXTERNAL_SCRAPER"


class FilterReason(str, Enum):
    DUPLICATE_JOB = "DUPLICATE_JOB"
    LOCATION_MISMATCH = "LOCATION_MISMATCH"
    ROLE_MISMATCH = "ROLE_MISMATCH"
    EXPERIENCE_MISMATCH = "EXPERIENCE_MISMATCH"
    SPONSORSHIP_MISMATCH = "SPONSORSHIP_MISMATCH"
