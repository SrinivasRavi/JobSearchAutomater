"""Abstract base class and result type for ATS form fillers."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.models.user_profile import UserProfile


@dataclass
class FillResult:
    success: bool
    fields_filled: list[str]
    fields_skipped: list[str]
    error: str = ""


class BaseFormFiller(ABC):
    def __init__(self, profile: UserProfile):
        self.profile = profile

    @abstractmethod
    def platform_name(self) -> str:
        """Return the ATS platform identifier, e.g. 'workday', 'oracle_hcm'."""

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this filler handles the given application URL."""

    @abstractmethod
    def fill_form(self, page) -> FillResult:
        """Fill form fields on the Playwright page. Returns FillResult."""

    @abstractmethod
    def submit(self, page) -> bool:
        """Click the submit button. Returns True on success."""
