"""Filler registry — maps ATS URLs to the correct BaseFormFiller subclass."""
from typing import Optional

from src.applier.base import BaseFormFiller
from src.models.user_profile import UserProfile

_FILLER_CLASSES: list[type[BaseFormFiller]] = []


def register_filler(filler_class: type[BaseFormFiller]) -> None:
    """Register a form filler class. Called at module import by each filler."""
    if filler_class not in _FILLER_CLASSES:
        _FILLER_CLASSES.append(filler_class)


def get_filler_for_url(url: str, profile: UserProfile) -> Optional[BaseFormFiller]:
    """Return an instantiated filler for the given URL, or None if unsupported."""
    for cls in _FILLER_CLASSES:
        instance = cls(profile)
        if instance.can_handle(url):
            return instance
    return None
