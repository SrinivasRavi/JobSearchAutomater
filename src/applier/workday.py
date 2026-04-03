"""Workday form filler — handles Nasdaq and other Workday ATS instances."""
from src.applier.base import BaseFormFiller, FillResult
from src.applier.registry import register_filler
from src.models.user_profile import UserProfile

# Workday uses data-automation-id attributes and aria-labels
# Each entry is (field_name, selector)
_FIELD_SELECTORS = [
    ("first_name", "[data-automation-id='legalNameSection_firstName']"),
    ("first_name", "input[aria-label*='First Name']"),
    ("first_name", "input[aria-label*='firstName']"),
    ("last_name", "[data-automation-id='legalNameSection_lastName']"),
    ("last_name", "input[aria-label*='Last Name']"),
    ("last_name", "input[aria-label*='lastName']"),
    ("email", "[data-automation-id='email']"),
    ("email", "input[aria-label*='Email']"),
    ("phone", "[data-automation-id='phone-number']"),
    ("phone", "input[aria-label*='Phone']"),
    ("city", "[data-automation-id='addressSection_city']"),
    ("city", "input[aria-label*='City']"),
    ("zip_code", "[data-automation-id='addressSection_postalCode']"),
    ("zip_code", "input[aria-label*='Postal']"),
    ("zip_code", "input[aria-label*='Zip']"),
]

_SUBMIT_SELECTORS = [
    "button[data-automation-id='bottom-navigation-next-button']",
    "button[data-automation-id='bottom-navigation-submit-button']",
    "button:has-text('Submit')",
    "button:has-text('Next')",
    "button:has-text('Save and Continue')",
]


class WorkdayFiller(BaseFormFiller):
    def platform_name(self) -> str:
        return "workday"

    def can_handle(self, url: str) -> bool:
        return "myworkdayjobs.com" in url or "workday.com" in url

    def fill_form(self, page) -> FillResult:
        profile = self.profile
        field_values = {
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "email": profile.email,
            "phone": profile.phone,
            "city": profile.city,
            "zip_code": profile.zip_code,
        }

        filled: list[str] = []
        skipped: list[str] = []
        seen_fields: set[str] = set()

        for field_name, selector in _FIELD_SELECTORS:
            if field_name in seen_fields:
                continue
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.fill(field_values[field_name])
                filled.append(field_name)
                seen_fields.add(field_name)

        for field_name in field_values:
            if field_name not in seen_fields:
                skipped.append(field_name)

        # Resume upload
        file_el = page.query_selector("input[type='file']")
        if file_el and file_el.is_visible():
            page.set_input_files("input[type='file']", profile.resume_path)
            filled.append("resume")
        else:
            skipped.append("resume")

        return FillResult(
            success=len(filled) > 0,
            fields_filled=filled,
            fields_skipped=skipped,
        )

    def submit(self, page) -> bool:
        for selector in _SUBMIT_SELECTORS:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click()
                return True
        return False


register_filler(WorkdayFiller)
