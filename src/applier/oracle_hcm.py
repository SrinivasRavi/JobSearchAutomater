"""Oracle HCM form filler — handles JPMorgan, Oracle, and other Taleo/OracleCloud ATS.

Flow:
1. Job detail page → click "Apply" button
2. Handle guest/login prompt → click "Apply as Guest" or equivalent
3. Wait for form to load
4. Fill personal info fields
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
    "button:has-text('Apply Now')",
    "a:has-text('Apply Now')",
    "[data-action='apply']",
]

# Selectors for guest/login choice after clicking Apply
_GUEST_APPLY_SELECTORS = [
    "button:has-text('Apply as Guest')",
    "a:has-text('Apply as Guest')",
    "button:has-text('Continue without signing in')",
    "a:has-text('Continue without signing in')",
    "button:has-text('Apply without an Account')",
    "a:has-text('Apply without an Account')",
    "button:has-text('Continue as Guest')",
    "a:has-text('Continue as Guest')",
]

# Selectors for Oracle HCM / Taleo forms
_FIELD_SELECTORS = [
    ("first_name", "input[aria-label*='First']"),
    ("first_name", "input[aria-label*='first']"),
    ("last_name", "input[aria-label*='Last']"),
    ("last_name", "input[aria-label*='last']"),
    ("email", "input[aria-label*='Email']"),
    ("email", "input[aria-label*='email']"),
    ("phone", "input[aria-label*='Phone']"),
    ("phone", "input[aria-label*='phone']"),
]

_SUBMIT_SELECTORS = [
    "button:has-text('Submit')",
    "button:has-text('Submit Application')",
    "input[type='submit']",
]


class OracleHCMFiller(BaseFormFiller):
    def platform_name(self) -> str:
        return "oracle_hcm"

    def can_handle(self, url: str) -> bool:
        return (
            "taleo.net" in url
            or "oraclecloud.com" in url
            or "fa.us" in url and "oraclecloud" in url
        )

    def _navigate_to_form(self, page) -> bool:
        """Click Apply → handle guest/login → wait for form. Returns True if form loaded."""
        # Step 1: Click "Apply" button on job detail page
        for selector in _APPLY_BUTTON_SELECTORS:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                logger.info("Clicking Apply button: %s", selector)
                btn.click()
                page.wait_for_timeout(3000)
                break

        # Step 2: Handle guest/login prompt
        for selector in _GUEST_APPLY_SELECTORS:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                logger.info("Clicking guest apply: %s", selector)
                btn.click()
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(3000)
                return True

        # Maybe we're already on the form (no guest prompt)
        return True

    def fill_form(self, page) -> FillResult:
        self._navigate_to_form(page)

        profile = self.profile
        field_values = {
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "email": profile.email,
            "phone": profile.phone,
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

        # Track which fields were never found
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


register_filler(OracleHCMFiller)
