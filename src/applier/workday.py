"""Workday form filler — handles Nasdaq and other Workday ATS instances.

Flow:
1. Job detail page → click "Apply" button
2. "Start Your Application" modal → click "Apply Manually"
3. Wait for form to load
4. Fill personal info fields on "My Information" page
"""
import logging

from src.applier.base import BaseFormFiller, FillResult
from src.applier.registry import register_filler
from src.models.user_profile import UserProfile

logger = logging.getLogger(__name__)

# Selectors to click the Apply button on the job detail page
_APPLY_BUTTON_SELECTORS = [
    "button:has-text('Apply')",
    "a:has-text('Apply')",
    "[data-automation-id='jobPostingApplyButton']",
]

# Selectors for the "Start Your Application" modal
_APPLY_MANUALLY_SELECTORS = [
    "button:has-text('Apply Manually')",
    "a:has-text('Apply Manually')",
    "button:has-text('Apply manually')",
    # Fallback: "Autofill with Resume" is also acceptable
    "button:has-text('Autofill with Resume')",
]

# Workday uses data-automation-id attributes and aria-labels
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

    def _navigate_to_form(self, page) -> bool:
        """Click Apply → handle modal → wait for form. Returns True if form loaded."""
        # Step 1: Click "Apply" button on job detail page
        for selector in _APPLY_BUTTON_SELECTORS:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                logger.info("Clicking Apply button: %s", selector)
                btn.click()
                page.wait_for_timeout(3000)
                break

        # Step 2: Handle "Start Your Application" modal
        for selector in _APPLY_MANUALLY_SELECTORS:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                logger.info("Clicking application method: %s", selector)
                btn.click()
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(3000)
                return True

        # Maybe we're already on the form (no modal), or modal didn't appear
        return True

    def fill_form(self, page) -> FillResult:
        self._navigate_to_form(page)

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
            page.set_input_files("input[type='file']", profile.resume_path_hint)
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
