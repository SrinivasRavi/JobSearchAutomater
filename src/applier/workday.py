"""Workday form filler — handles Nasdaq and other Workday ATS instances.

Flow (from real Nasdaq testing):
1. Job detail page → click "Apply" button
2. "Start Your Application" modal → click "Apply Manually"
3. "Create Account/Sign In" page → fill email, password, consent → click "Create Account"
4. Wait for "My Information" page to load
5. Fill personal info fields on "My Information" page
"""
import logging

from src.applier.base import BaseFormFiller, FillResult
from src.applier.registry import register_filler
from src.models.user_profile import UserProfile

logger = logging.getLogger(__name__)

# Step 1: Click the Apply button on the job detail page
_APPLY_BUTTON_SELECTORS = [
    "[data-automation-id='jobPostingApplyButton']",
    "button:has-text('Apply')",
    "a:has-text('Apply')",
]

# Step 2: "Start Your Application" modal choices
_APPLY_MANUALLY_SELECTORS = [
    "button:has-text('Apply Manually')",
    "a:has-text('Apply Manually')",
    "button:has-text('Apply manually')",
    "button:has-text('Autofill with Resume')",
]

# Step 3: Create Account page field selectors
_CREATE_ACCOUNT_EMAIL_SELECTORS = [
    "[data-automation-id='createAccountEmail']",
    "input[data-automation-id='email']",
    "input[aria-label*='Email Address']",
    "input[type='email']",
]

_CREATE_ACCOUNT_PASSWORD_SELECTORS = [
    "[data-automation-id='createAccountPassword']",
    "input[data-automation-id='password']",
    "input[aria-label*='Password']:not([aria-label*='Verify'])",
    "input[type='password']",
]

_CREATE_ACCOUNT_VERIFY_PASSWORD_SELECTORS = [
    "[data-automation-id='createAccountVerifyPassword']",
    "input[data-automation-id='verifyPassword']",
    "input[aria-label*='Verify New Password']",
    "input[aria-label*='Verify Password']",
    "input[aria-label*='Confirm Password']",
]

_CREATE_ACCOUNT_CONSENT_SELECTORS = [
    "[data-automation-id='createAccountCheckbox']",
    "input[type='checkbox'][data-automation-id*='consent']",
    "input[type='checkbox'][aria-label*='terms']",
    # Generic: the only checkbox on the Create Account page
    "input[type='checkbox']",
]

_CREATE_ACCOUNT_BUTTON_SELECTORS = [
    "[data-automation-id='createAccountSubmitButton']",
    "button:has-text('Create Account')",
    "a:has-text('Create Account')",
]

# Step 3 alt: Sign In instead of Create Account (if account already exists)
_SIGN_IN_SELECTORS = [
    "a:has-text('Sign In')",
    "button:has-text('Sign In')",
    "[data-automation-id='signInLink']",
]

_SIGN_IN_EMAIL_SELECTORS = [
    "[data-automation-id='signInEmailAddress']",
    "input[aria-label*='Email']",
    "input[type='email']",
]

_SIGN_IN_PASSWORD_SELECTORS = [
    "[data-automation-id='signInPassword']",
    "input[aria-label*='Password']",
    "input[type='password']",
]

_SIGN_IN_BUTTON_SELECTORS = [
    "[data-automation-id='signInSubmitButton']",
    "button:has-text('Sign In')",
]

# Workday uses data-automation-id attributes and aria-labels for form fields
_FIELD_SELECTORS = [
    ("first_name", "[data-automation-id='legalNameSection_firstName']"),
    ("first_name", "input[aria-label*='Given Name']"),
    ("first_name", "input[aria-label*='First Name']"),
    ("first_name", "input[aria-label*='firstName']"),
    ("last_name", "[data-automation-id='legalNameSection_lastName']"),
    ("last_name", "input[aria-label*='Family Name']"),
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

    def _click_first_visible(self, page, selectors: list[str], description: str) -> bool:
        """Try each selector in order, click the first visible element. Returns True if clicked."""
        for selector in selectors:
            try:
                el = page.query_selector(selector)
                if el and el.is_visible():
                    logger.info("Clicking %s: %s", description, selector)
                    el.click()
                    return True
            except Exception as e:
                logger.debug("Selector %s failed: %s", selector, e)
        logger.warning("No visible element found for: %s", description)
        return False

    def _fill_first_visible(self, page, selectors: list[str], value: str, description: str) -> bool:
        """Try each selector in order, fill the first visible element. Returns True if filled."""
        for selector in selectors:
            try:
                el = page.query_selector(selector)
                if el and el.is_visible():
                    logger.info("Filling %s: %s", description, selector)
                    el.fill(value)
                    return True
            except Exception as e:
                logger.debug("Selector %s failed: %s", selector, e)
        logger.warning("No visible element found for: %s", description)
        return False

    def _navigate_to_form(self, page) -> bool:
        """Navigate through Apply → modal → account creation → form. Returns True if form loaded."""

        # Step 1: Click "Apply" button on job detail page
        logger.info("Step 1: Looking for Apply button on job detail page")
        if self._click_first_visible(page, _APPLY_BUTTON_SELECTORS, "Apply button"):
            page.wait_for_timeout(3000)

        # Step 2: Handle "Start Your Application" modal
        logger.info("Step 2: Looking for Apply Manually in modal")
        if self._click_first_visible(page, _APPLY_MANUALLY_SELECTORS, "Apply Manually"):
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(3000)

        # Step 3: Handle "Create Account / Sign In" page
        # Check if we're on the Create Account page by looking for the page heading or form
        logger.info("Step 3: Checking for Create Account page")
        if self._is_create_account_page(page):
            logger.info("Create Account page detected — filling account creation form")
            self._handle_create_account(page)
        elif self._is_sign_in_page(page):
            logger.info("Sign In page detected — signing in")
            self._handle_sign_in(page)
        else:
            logger.info("No account page detected — may already be on form")

        return True

    def _is_create_account_page(self, page) -> bool:
        """Check if the current page is a Create Account page."""
        # Look for heading or button that says "Create Account"
        for selector in [
            "h2:has-text('Create Account')",
            "h1:has-text('Create Account')",
            "button:has-text('Create Account')",
            "[data-automation-id='createAccountSubmitButton']",
        ]:
            el = page.query_selector(selector)
            if el and el.is_visible():
                return True
        return False

    def _is_sign_in_page(self, page) -> bool:
        """Check if the current page is a Sign In page."""
        for selector in [
            "h2:has-text('Sign In')",
            "h1:has-text('Sign In')",
            "[data-automation-id='signInSubmitButton']",
        ]:
            el = page.query_selector(selector)
            if el and el.is_visible():
                return True
        return False

    def _handle_create_account(self, page) -> None:
        """Fill the Create Account form and submit it."""
        profile = self.profile

        # Fill email
        self._fill_first_visible(
            page, _CREATE_ACCOUNT_EMAIL_SELECTORS, profile.email, "account email"
        )
        page.wait_for_timeout(500)

        # Fill password
        password = profile.ats_password
        if not password:
            logger.error("No ats_password in profile — cannot create account")
            return

        # Find and fill password field (first password input)
        self._fill_password_fields(page, password)
        page.wait_for_timeout(500)

        # Check consent checkbox
        self._check_consent(page)
        page.wait_for_timeout(500)

        # Click Create Account
        if self._click_first_visible(page, _CREATE_ACCOUNT_BUTTON_SELECTORS, "Create Account"):
            logger.info("Clicked Create Account — waiting for next page")
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(5000)

    def _fill_password_fields(self, page, password: str) -> None:
        """Fill both password and verify password fields."""
        # Get all password inputs on the page
        password_inputs = page.query_selector_all("input[type='password']")
        if len(password_inputs) >= 2:
            # First is password, second is verify
            logger.info("Found %d password fields — filling both", len(password_inputs))
            if password_inputs[0].is_visible():
                password_inputs[0].fill(password)
            if password_inputs[1].is_visible():
                password_inputs[1].fill(password)
        elif len(password_inputs) == 1:
            # Only one password field (sign-in page?)
            if password_inputs[0].is_visible():
                password_inputs[0].fill(password)
        else:
            # Fallback to named selectors
            self._fill_first_visible(
                page, _CREATE_ACCOUNT_PASSWORD_SELECTORS, password, "password"
            )
            self._fill_first_visible(
                page, _CREATE_ACCOUNT_VERIFY_PASSWORD_SELECTORS, password, "verify password"
            )

    def _check_consent(self, page) -> None:
        """Check the consent/terms checkbox if present."""
        for selector in _CREATE_ACCOUNT_CONSENT_SELECTORS:
            try:
                el = page.query_selector(selector)
                if el and el.is_visible():
                    # Only click if not already checked
                    if not el.is_checked():
                        logger.info("Checking consent checkbox: %s", selector)
                        el.click()
                    else:
                        logger.info("Consent checkbox already checked")
                    return
            except Exception as e:
                logger.debug("Consent selector %s failed: %s", selector, e)

    def _handle_sign_in(self, page) -> None:
        """Sign in with existing account."""
        profile = self.profile
        self._fill_first_visible(
            page, _SIGN_IN_EMAIL_SELECTORS, profile.email, "sign-in email"
        )
        if profile.ats_password:
            password_inputs = page.query_selector_all("input[type='password']")
            if password_inputs and password_inputs[0].is_visible():
                password_inputs[0].fill(profile.ats_password)
        if self._click_first_visible(page, _SIGN_IN_BUTTON_SELECTORS, "Sign In"):
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(5000)

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
