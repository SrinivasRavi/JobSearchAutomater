"""Workday form filler — handles Nasdaq and other Workday ATS instances.

Flow (from real Nasdaq testing):
1. Job detail page → click "Apply" button
2. "Start Your Application" modal → click "Apply Manually"
3. "Create Account/Sign In" page → fill email, password, consent → click "Create Account"
4. Wait for "My Information" page to load
5. Fill personal info fields on "My Information" page

Key Workday quirk: ALL buttons are wrapped in a <div data-automation-id="click_filter">
overlay that intercepts pointer events. We must use force=True on all clicks, or target
the overlay div directly via page.locator().click(force=True).
"""
import logging
import os

from src.applier.base import BaseFormFiller, FillResult
from src.applier.registry import register_filler
from src.models.user_profile import UserProfile

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "screenshots",
)

# Step 1: Click the Apply button on the job detail page
_APPLY_BUTTON_SELECTORS = [
    "[data-automation-id='jobPostingApplyButton']",
    "a:has-text('Apply')",
    "button:has-text('Apply')",
]

# Step 2: "Start Your Application" modal choices
_APPLY_MANUALLY_SELECTORS = [
    "a:has-text('Apply Manually')",
    "button:has-text('Apply Manually')",
    "a:has-text('Apply manually')",
    "button:has-text('Apply manually')",
    "a:has-text('Autofill with Resume')",
    "button:has-text('Autofill with Resume')",
]

# Step 3: Create Account page field selectors
_CREATE_ACCOUNT_EMAIL_SELECTORS = [
    "[data-automation-id='createAccountEmail']",
    "input[data-automation-id='email']",
    "input[aria-label*='Email Address']",
    "input[type='email']",
]

_CREATE_ACCOUNT_BUTTON_SELECTORS = [
    # Target the overlay div that actually receives clicks in Workday
    "div[data-automation-id='click_filter'][aria-label='Create Account']",
    "[data-automation-id='createAccountSubmitButton']",
    "button:has-text('Create Account')",
]

_CREATE_ACCOUNT_CONSENT_SELECTORS = [
    "[data-automation-id='createAccountCheckbox']",
    "input[type='checkbox'][data-automation-id*='consent']",
    "input[type='checkbox'][aria-label*='terms']",
    "input[type='checkbox']",
]

# Sign In selectors (if account already exists)
_SIGN_IN_LINK_SELECTORS = [
    "a:has-text('Sign In')",
    "button:has-text('Sign In')",
    "[data-automation-id='signInLink']",
]

_SIGN_IN_BUTTON_SELECTORS = [
    "div[data-automation-id='click_filter'][aria-label='Sign In']",
    "[data-automation-id='signInSubmitButton']",
    "button:has-text('Sign In')",
]

# Workday form field selectors (My Information page)
_FIELD_SELECTORS = [
    ("first_name", "[data-automation-id='legalNameSection_firstName']"),
    ("first_name", "input[aria-label*='Given Name']"),
    ("first_name", "input[aria-label*='First Name']"),
    ("last_name", "[data-automation-id='legalNameSection_lastName']"),
    ("last_name", "input[aria-label*='Family Name']"),
    ("last_name", "input[aria-label*='Last Name']"),
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
    """Workday ATS form filler.

    Uses Playwright locators with force=True for all clicks because Workday
    wraps buttons in <div data-automation-id="click_filter"> overlays that
    intercept pointer events.
    """

    def __init__(self, profile: UserProfile):
        super().__init__(profile)
        self._screenshot_counter = 0

    def platform_name(self) -> str:
        return "workday"

    def can_handle(self, url: str) -> bool:
        return "myworkdayjobs.com" in url or "workday.com" in url

    def _take_screenshot(self, page, label: str) -> None:
        """Take a debug screenshot at each navigation step."""
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        self._screenshot_counter += 1
        path = os.path.join(SCREENSHOTS_DIR, f"workday_step_{self._screenshot_counter}_{label}.png")
        try:
            page.screenshot(path=path)
            logger.info("Screenshot saved: %s", path)
        except Exception as e:
            logger.debug("Screenshot failed: %s", e)

    def _click(self, page, selector: str, description: str, timeout: int = 10000) -> bool:
        """Click an element using Playwright locator with force=True.

        force=True bypasses Workday's click_filter overlay divs that
        intercept pointer events on all buttons.
        """
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)
            logger.info("Clicking %s: %s", description, selector)
            locator.click(force=True, timeout=5000)
            return True
        except Exception as e:
            logger.debug("Click failed for %s [%s]: %s", description, selector, e)
            return False

    def _click_any(self, page, selectors: list[str], description: str, timeout: int = 10000) -> bool:
        """Try each selector, click the first one found. Uses force=True."""
        for selector in selectors:
            if self._click(page, selector, description, timeout=timeout):
                return True
        logger.warning("No element found for: %s", description)
        return False

    def _fill_field(self, page, selector: str, value: str, description: str, timeout: int = 10000) -> bool:
        """Fill a field using Playwright locator with auto-waiting."""
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)
            logger.info("Filling %s: %s", description, selector)
            locator.fill(value)
            return True
        except Exception as e:
            logger.debug("Fill failed for %s [%s]: %s", description, selector, e)
            return False

    def _fill_any(self, page, selectors: list[str], value: str, description: str, timeout: int = 10000) -> bool:
        """Try each selector, fill the first one found."""
        for selector in selectors:
            if self._fill_field(page, selector, value, description, timeout=timeout):
                return True
        logger.warning("No element found to fill: %s", description)
        return False

    def _navigate_to_form(self, page) -> bool:
        """Navigate through Apply → modal → account creation → form."""

        # Step 1: Click "Apply" button on job detail page
        logger.info("=== Step 1: Click Apply button ===")
        self._take_screenshot(page, "before_apply")
        if self._click_any(page, _APPLY_BUTTON_SELECTORS, "Apply button", timeout=15000):
            page.wait_for_timeout(3000)
            self._take_screenshot(page, "after_apply")
        else:
            logger.error("Apply button not found — cannot proceed")
            self._take_screenshot(page, "apply_failed")
            return False

        # Step 2: Handle "Start Your Application" modal
        logger.info("=== Step 2: Click Apply Manually in modal ===")
        if self._click_any(page, _APPLY_MANUALLY_SELECTORS, "Apply Manually", timeout=10000):
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)
            self._take_screenshot(page, "after_apply_manually")

        # Step 3: Handle "Create Account / Sign In" page
        logger.info("=== Step 3: Account creation or sign-in ===")
        if self._is_create_account_page(page):
            logger.info("Create Account page detected")
            self._handle_create_account(page)
            self._take_screenshot(page, "after_create_account")
        elif self._is_sign_in_page(page):
            logger.info("Sign In page detected")
            self._handle_sign_in(page)
            self._take_screenshot(page, "after_sign_in")
        else:
            logger.info("No account page — may already be on form")
            self._take_screenshot(page, "no_account_page")

        return True

    def _is_create_account_page(self, page) -> bool:
        """Check if we're on the Create Account page."""
        try:
            page.locator("h2:has-text('Create Account'), h1:has-text('Create Account')").first.wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    def _is_sign_in_page(self, page) -> bool:
        """Check if we're on a Sign In page."""
        try:
            page.locator("h2:has-text('Sign In'), h1:has-text('Sign In')").first.wait_for(
                state="visible", timeout=3000
            )
            return True
        except Exception:
            return False

    def _handle_create_account(self, page) -> None:
        """Fill the Create Account form and submit it."""
        profile = self.profile

        # Fill email
        self._fill_any(
            page, _CREATE_ACCOUNT_EMAIL_SELECTORS, profile.email, "account email", timeout=10000
        )
        page.wait_for_timeout(500)

        # Fill password fields
        password = profile.ats_password
        if not password:
            logger.error("No ats_password in profile — cannot create account")
            return

        password_inputs = page.locator("input[type='password']")
        count = password_inputs.count()
        logger.info("Found %d password fields", count)
        if count >= 2:
            password_inputs.nth(0).fill(password)
            page.wait_for_timeout(300)
            password_inputs.nth(1).fill(password)
        elif count == 1:
            password_inputs.nth(0).fill(password)
        page.wait_for_timeout(500)

        # Check consent checkbox
        try:
            checkbox = page.locator("input[type='checkbox']").first
            if checkbox.is_visible() and not checkbox.is_checked():
                logger.info("Checking consent checkbox")
                checkbox.click(force=True)
                page.wait_for_timeout(500)
        except Exception as e:
            logger.warning("Consent checkbox not found: %s", e)

        self._take_screenshot(page, "before_create_account_click")

        # Click Create Account button
        logger.info("Clicking Create Account button")
        if self._click_any(page, _CREATE_ACCOUNT_BUTTON_SELECTORS, "Create Account", timeout=10000):
            logger.info("Clicked Create Account — waiting for next page to load")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)
            self._take_screenshot(page, "after_create_account_submit")
        else:
            logger.error("Failed to click Create Account button")
            self._take_screenshot(page, "create_account_click_failed")

    def _handle_sign_in(self, page) -> None:
        """Sign in with existing account."""
        profile = self.profile

        # Fill email
        self._fill_any(
            page, [
                "[data-automation-id='signInEmailAddress']",
                "input[aria-label*='Email']",
                "input[type='email']",
            ],
            profile.email, "sign-in email", timeout=10000
        )

        # Fill password
        if profile.ats_password:
            password_input = page.locator("input[type='password']").first
            try:
                password_input.wait_for(state="visible", timeout=5000)
                password_input.fill(profile.ats_password)
            except Exception as e:
                logger.warning("Sign-in password field not found: %s", e)

        # Click Sign In
        if self._click_any(page, _SIGN_IN_BUTTON_SELECTORS, "Sign In", timeout=5000):
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)

    def fill_form(self, page) -> FillResult:
        self._navigate_to_form(page)

        self._take_screenshot(page, "before_fill_form")

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
            try:
                locator = page.locator(selector).first
                if locator.is_visible():
                    locator.fill(field_values[field_name])
                    filled.append(field_name)
                    seen_fields.add(field_name)
                    logger.info("Filled %s via %s", field_name, selector)
            except Exception:
                pass

        for field_name in field_values:
            if field_name not in seen_fields:
                skipped.append(field_name)

        # Resume upload
        file_input = page.locator("input[type='file']")
        try:
            if file_input.count() > 0 and file_input.first.is_visible():
                page.set_input_files("input[type='file']", profile.resume_path_hint)
                filled.append("resume")
            else:
                skipped.append("resume")
        except Exception:
            skipped.append("resume")

        self._take_screenshot(page, "after_fill_form")

        return FillResult(
            success=len(filled) > 0,
            fields_filled=filled,
            fields_skipped=skipped,
        )

    def submit(self, page) -> bool:
        for selector in _SUBMIT_SELECTORS:
            if self._click(page, selector, "Submit", timeout=3000):
                return True
        return False


register_filler(WorkdayFiller)
