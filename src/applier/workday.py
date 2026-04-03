"""Workday form filler — handles Nasdaq and other Workday ATS instances.

Revised flow (Sign In first strategy):
1. Job detail page → click "Apply" button
2. "Start Your Application" modal → click "Apply Manually"
3. Account page → try Sign In first (account likely exists from prior runs).
   If no account, fall back to Create Account.
4. Fill fields on every wizard page (My Information, My Experience, etc.)
5. Human reviews and confirms submission on Review page.

Key Workday quirk: ALL buttons are wrapped in a <div data-automation-id="click_filter">
overlay that intercepts pointer events. We must use force=True on all clicks.
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

# --- Selectors ---

_APPLY_BUTTON_SELECTORS = [
    "[data-automation-id='jobPostingApplyButton']",
    "a:has-text('Apply')",
    "button:has-text('Apply')",
]

_APPLY_MANUALLY_SELECTORS = [
    "a:has-text('Apply Manually')",
    "button:has-text('Apply Manually')",
    "a:has-text('Apply manually')",
    "button:has-text('Apply manually')",
    "a:has-text('Autofill with Resume')",
    "button:has-text('Autofill with Resume')",
]

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

_CREATE_ACCOUNT_EMAIL_SELECTORS = [
    "[data-automation-id='createAccountEmail']",
    "input[data-automation-id='email']",
    "input[aria-label*='Email Address']",
    "input[type='email']",
]

_CREATE_ACCOUNT_BUTTON_SELECTORS = [
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

# Form field selectors — discovered via real Nasdaq testing.
# Workday uses name= and id= attributes on the My Information page,
# but data-automation-id on the Create Account page.
_FIELD_SELECTORS = [
    ("first_name", "input[id='name--legalName--firstName']"),
    ("first_name", "input[name='legalName--firstName']"),
    ("first_name", "[data-automation-id='legalNameSection_firstName']"),
    ("first_name", "input[aria-label*='Given Name']"),
    ("last_name", "input[id='name--legalName--lastName']"),
    ("last_name", "input[name='legalName--lastName']"),
    ("last_name", "[data-automation-id='legalNameSection_lastName']"),
    ("last_name", "input[aria-label*='Family Name']"),
    ("phone", "input[id='phoneNumber--phoneNumber']"),
    ("phone", "input[name='phoneNumber']"),
    ("phone", "[data-automation-id='phone-number']"),
    ("phone", "input[aria-label*='Phone']"),
    ("city", "input[id='address--city']"),
    ("city", "input[name='city']"),
    ("city", "[data-automation-id='addressSection_city']"),
    ("city", "input[aria-label*='City']"),
    ("zip_code", "input[id='address--postalCode']"),
    ("zip_code", "input[name='postalCode']"),
    ("zip_code", "[data-automation-id='addressSection_postalCode']"),
    ("zip_code", "input[aria-label*='Postal']"),
    ("email", "[data-automation-id='email']"),
    ("email", "input[aria-label*='Email']"),
]

_SUBMIT_SELECTORS = [
    "button[data-automation-id='bottom-navigation-next-button']",
    "button[data-automation-id='bottom-navigation-submit-button']",
    "button:has-text('Submit')",
    "button:has-text('Next')",
    "button:has-text('Save and Continue')",
]


class WorkdayFiller(BaseFormFiller):
    """Workday ATS form filler."""

    def __init__(self, profile: UserProfile):
        super().__init__(profile)
        self._screenshot_counter = 0

    def platform_name(self) -> str:
        return "workday"

    def can_handle(self, url: str) -> bool:
        return "myworkdayjobs.com" in url or "workday.com" in url

    # --- Low-level helpers ---

    def _take_screenshot(self, page, label: str) -> None:
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        self._screenshot_counter += 1
        path = os.path.join(SCREENSHOTS_DIR, f"workday_step_{self._screenshot_counter}_{label}.png")
        try:
            page.screenshot(path=path, full_page=True)
        except Exception:
            pass

    def _click(self, page, selector: str, description: str, timeout: int = 10000) -> bool:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)
            locator.click(force=True, timeout=5000)
            print(f"  [click] {description}")
            return True
        except Exception:
            return False

    def _click_any(self, page, selectors: list[str], description: str, timeout: int = 10000) -> bool:
        for selector in selectors:
            if self._click(page, selector, description, timeout=timeout):
                return True
        print(f"  [miss]  {description} — no matching element")
        return False

    def _fill_field(self, page, selector: str, value: str, description: str, timeout: int = 10000) -> bool:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)
            locator.fill(value)
            print(f"  [fill]  {description} = {value[:30]}")
            return True
        except Exception:
            return False

    def _fill_any(self, page, selectors: list[str], value: str, description: str, timeout: int = 10000) -> bool:
        for selector in selectors:
            if self._fill_field(page, selector, value, description, timeout=timeout):
                return True
        return False

    def _wait_and_screenshot(self, page, label: str, wait_ms: int = 3000) -> None:
        page.wait_for_timeout(wait_ms)
        self._take_screenshot(page, label)

    def _debug_inputs(self, page) -> None:
        """Print all input fields on current page for debugging."""
        try:
            all_inputs = page.locator("input").all()
            print(f"  [debug] {len(all_inputs)} input fields on page:")
            for i, inp in enumerate(all_inputs):
                try:
                    attrs = page.evaluate(
                        """(el) => ({
                            type: el.type,
                            id: el.id,
                            name: el.name,
                            'data-automation-id': el.getAttribute('data-automation-id'),
                            visible: el.offsetParent !== null
                        })""",
                        inp.element_handle(),
                    )
                    if attrs.get("visible"):
                        print(f"          {i}: {attrs}")
                except Exception:
                    pass
        except Exception:
            pass

    # --- Navigation ---

    def _navigate_to_form(self, page) -> bool:
        """Navigate: Apply → modal → Sign In → My Information."""

        # Step 1: Click Apply
        print("  Step 1: Click Apply button")
        self._take_screenshot(page, "before_apply")
        if not self._click_any(page, _APPLY_BUTTON_SELECTORS, "Apply button", timeout=15000):
            print("  FAILED: Apply button not found")
            self._take_screenshot(page, "apply_failed")
            return False
        self._wait_and_screenshot(page, "after_apply", 3000)

        # Step 2: Handle modal (may or may not appear)
        print("  Step 2: Handle Apply Manually modal")
        if self._click_any(page, _APPLY_MANUALLY_SELECTORS, "Apply Manually", timeout=8000):
            self._wait_and_screenshot(page, "after_apply_manually", 5000)
        else:
            # Modal might not appear — page may go directly to account page
            self._wait_and_screenshot(page, "no_modal", 3000)

        # Step 3: Sign In (preferred) or Create Account
        print("  Step 3: Sign In or Create Account")
        self._handle_account(page)

        return True

    def _handle_account(self, page) -> None:
        """Handle the account page. Try Sign In first, fall back to Create Account.

        Strategy: Count password fields to distinguish pages.
        - 2+ password fields → Create Account page (password + verify)
        - 1 password field → Sign In page
        - 0 password fields → already on form or unknown
        """

        # Wait a moment for the page to settle
        page.wait_for_timeout(2000)

        # Count password fields to determine page type
        try:
            pw_count = page.locator("input[type='password']").count()
        except Exception:
            pw_count = 0

        print(f"  Password fields found: {pw_count}")

        if pw_count == 1:
            # Sign In page (1 password field)
            print("  Sign In page detected (1 password field)")
            self._do_sign_in(page)
            return

        if pw_count >= 2:
            # Create Account page (password + verify) — but try clicking Sign In link first
            print("  Create Account page detected (2+ password fields)")
            # Try to switch to Sign In since account likely exists
            sign_in_clicked = False
            for sel in _SIGN_IN_LINK_SELECTORS:
                if self._click(page, sel, "Sign In link", timeout=3000):
                    sign_in_clicked = True
                    break
            if sign_in_clicked:
                self._wait_and_screenshot(page, "switched_to_sign_in", 3000)
                self._do_sign_in(page)
            else:
                # No Sign In link found — create new account
                print("  No Sign In link — creating new account")
                self._do_create_account(page)
            return

        # No password fields — check for Sign In modal
        if self._has_sign_in_modal(page):
            print("  Sign In modal detected")
            self._do_sign_in(page)
            return

        # Maybe we're already on the form
        print("  No account page detected — may already be on form")
        self._take_screenshot(page, "no_account_page")

    def _has_element(self, page, selector: str, timeout: int = 3000) -> bool:
        try:
            page.locator(selector).first.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    def _has_sign_in_modal(self, page) -> bool:
        """Check for Sign In modal overlay (seen after clicking Apply on some jobs)."""
        try:
            # Workday sometimes shows a Sign In modal with Nasdaq logo
            modal = page.locator("[role='dialog']:has-text('Sign In')").first
            modal.wait_for(state="visible", timeout=3000)
            return True
        except Exception:
            return False

    def _do_sign_in(self, page) -> None:
        """Fill and submit the Sign In form.

        Workday may show Sign In as:
        - A modal/dialog overlay on top of Create Account page
        - A full standalone page
        We scope selectors to the modal if one exists.
        """
        profile = self.profile

        # Check if Sign In is in a modal dialog
        modal = None
        try:
            modal_loc = page.locator("[role='dialog']").first
            modal_loc.wait_for(state="visible", timeout=3000)
            modal = modal_loc
            print("  Sign In is in a modal dialog — scoping selectors")
        except Exception:
            pass

        # Scope selectors to modal if present
        scope = modal if modal else page

        # Fill email
        email_filled = False
        email_selectors = [
            "input[data-automation-id='email']",
            "[data-automation-id='signInEmailAddress']",
            "input[aria-label*='Email']",
            "input[type='email']",
            "input[type='text']",
        ]
        for sel in email_selectors:
            try:
                loc = scope.locator(sel).first
                loc.wait_for(state="visible", timeout=3000)
                loc.fill(profile.email)
                print(f"  [fill]  sign-in email = {profile.email}")
                email_filled = True
                break
            except Exception:
                continue
        if not email_filled:
            print("  FAILED: Could not fill email on Sign In")

        # Fill password
        if profile.ats_password:
            try:
                pw = scope.locator("input[type='password']").first
                pw.wait_for(state="visible", timeout=3000)
                pw.fill(profile.ats_password)
                print("  [fill]  sign-in password")
            except Exception:
                print("  [miss]  sign-in password field not found")

        self._take_screenshot(page, "sign_in_filled")

        # Click Sign In button (scope to modal if present)
        sign_in_clicked = False
        for sel in _SIGN_IN_BUTTON_SELECTORS:
            try:
                btn = scope.locator(sel).first
                btn.wait_for(state="visible", timeout=3000)
                btn.click(force=True, timeout=5000)
                print(f"  [click] Sign In button")
                sign_in_clicked = True
                break
            except Exception:
                continue

        if sign_in_clicked:
            self._wait_for_form_page(page, "after_sign_in")
        else:
            print("  FAILED: Sign In button not found")
            self._take_screenshot(page, "sign_in_button_failed")

    def _do_create_account(self, page) -> None:
        """Fill and submit the Create Account form."""
        profile = self.profile

        # Email
        self._fill_any(page, _CREATE_ACCOUNT_EMAIL_SELECTORS, profile.email, "account email", timeout=10000)
        page.wait_for_timeout(500)

        # Password fields
        if not profile.ats_password:
            print("  FAILED: No ats_password in profile")
            return

        pw_inputs = page.locator("input[type='password']")
        count = pw_inputs.count()
        if count >= 2:
            pw_inputs.nth(0).fill(profile.ats_password)
            page.wait_for_timeout(300)
            pw_inputs.nth(1).fill(profile.ats_password)
            print(f"  [fill]  password x2")
        elif count == 1:
            pw_inputs.nth(0).fill(profile.ats_password)
            print(f"  [fill]  password x1")

        # Consent checkbox
        try:
            cb = page.locator("input[type='checkbox']").first
            if cb.is_visible() and not cb.is_checked():
                cb.click(force=True)
                print("  [click] consent checkbox")
        except Exception:
            pass

        self._take_screenshot(page, "before_create_account_click")

        # Click Create Account
        if self._click_any(page, _CREATE_ACCOUNT_BUTTON_SELECTORS, "Create Account", timeout=10000):
            self._wait_for_form_page(page, "after_create_account")
        else:
            print("  FAILED: Create Account button not found")
            # Maybe account already exists — check for Sign In redirect
            self._take_screenshot(page, "create_account_failed")
            if self._has_element(page, "a:has-text('Sign In')", 3000):
                self._click_any(page, _SIGN_IN_LINK_SELECTORS, "Sign In fallback", timeout=5000)
                page.wait_for_timeout(2000)
                self._do_sign_in(page)

    def _wait_for_form_page(self, page, label: str) -> None:
        """Wait for a Workday form page to load after sign-in or account creation."""
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(3000)

        # Check what page we landed on — use short timeouts
        # NOTE: "text=My Information" matches the progress bar on ALL pages — don't use it!
        # Use actual form field selectors that only appear on the form page.
        form_indicators = [
            "input[id='name--legalName--firstName']",
            "input[name='legalName--firstName']",
            "input[id='source--source']",
            "text=How Did You Hear",
        ]
        for sel in form_indicators:
            if self._has_element(page, sel, 2000):
                print(f"  Form page loaded (detected: {sel})")
                self._take_screenshot(page, label)
                return

        # Check for Sign In page (account exists redirect after Create Account)
        if self._has_element(page, "text=Sign In", 2000):
            print("  Redirected to Sign In after account action")
            self._take_screenshot(page, "redirected_sign_in")
            self._do_sign_in(page)
            # After sign in, wait again for form page (no recursion — just one more check)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            page.wait_for_timeout(3000)
            for sel in form_indicators:
                if self._has_element(page, sel, 3000):
                    print(f"  Form page loaded after sign-in (detected: {sel})")
                    self._take_screenshot(page, "form_after_sign_in")
                    return
            self._take_screenshot(page, "after_sign_in_unknown")
            return

        # Unknown state — screenshot for diagnosis
        print("  WARNING: Unknown page state after account action")
        self._take_screenshot(page, label + "_unknown")

    # --- Form filling ---

    def fill_form(self, page) -> FillResult:
        self._navigate_to_form(page)
        self._take_screenshot(page, "before_fill")

        # Scroll to load all lazy fields
        for pos in [500, 1000, 1500, 2000, 3000]:
            page.evaluate(f"window.scrollTo(0, {pos})")
            page.wait_for_timeout(300)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

        self._debug_inputs(page)

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
        seen: set[str] = set()

        # Fill known fields via selectors
        for field_name, selector in _FIELD_SELECTORS:
            if field_name in seen:
                continue
            try:
                loc = page.locator(selector).first
                try:
                    loc.scroll_into_view_if_needed(timeout=2000)
                except Exception:
                    pass
                if loc.is_visible():
                    value = field_values[field_name]
                    # Strip country code for phone — Workday has a separate country code dropdown
                    if field_name == "phone":
                        value = self._strip_country_code(value)
                    loc.fill(value)
                    filled.append(field_name)
                    seen.add(field_name)
                    print(f"  [fill]  {field_name} = {value}")
            except Exception:
                pass

        # Try to fill radio buttons (e.g., "Previously worked for Nasdaq?")
        self._fill_radio_no(page, "candidateIsPreviousWorker")

        # Try to fill address line if visible
        try:
            addr_loc = page.locator("input[id='address--addressLine1'], input[name='addressLine1']").first
            addr_loc.scroll_into_view_if_needed(timeout=2000)
            if addr_loc.is_visible():
                addr_loc.fill("Mumbai")
                filled.append("address")
                print("  [fill]  address = Mumbai")
        except Exception:
            pass

        for field_name in field_values:
            if field_name not in seen:
                skipped.append(field_name)

        # Resume upload
        try:
            file_input = page.locator("input[type='file']")
            if file_input.count() > 0:
                page.set_input_files("input[type='file']", profile.resume_path_hint)
                filled.append("resume")
                print(f"  [fill]  resume = {profile.resume_path_hint}")
            else:
                skipped.append("resume")
        except Exception:
            skipped.append("resume")

        self._take_screenshot(page, "after_fill")

        return FillResult(
            success=len(filled) > 0,
            fields_filled=filled,
            fields_skipped=skipped,
        )

    @staticmethod
    def _strip_country_code(phone: str) -> str:
        """Strip country code prefix from phone number for Workday's split phone input."""
        import re
        # Remove common country code patterns: +91-, +91, +1-, +1, etc.
        cleaned = re.sub(r'^\+?\d{1,3}[-\s]?', '', phone)
        # If the result looks too short, return original without +
        if len(cleaned) < 7:
            return phone.lstrip('+')
        return cleaned

    def _fill_radio_no(self, page, name: str) -> None:
        """Click the 'No' radio button for a given radio group."""
        try:
            # Find radio with name and value indicating 'No'
            radios = page.locator(f"input[name='{name}']")
            if radios.count() >= 2:
                # Second radio is typically "No"
                no_radio = radios.nth(1)
                if no_radio.is_visible():
                    no_radio.click(force=True)
                    print(f"  [click] radio '{name}' = No")
        except Exception:
            pass

    def submit(self, page) -> bool:
        for selector in _SUBMIT_SELECTORS:
            if self._click(page, selector, "Submit", timeout=3000):
                return True
        return False


# Keep old detection methods for test compatibility
WorkdayFiller._is_create_account_page = lambda self, page: self._has_element(page, "text=Create Account", 3000)
WorkdayFiller._is_sign_in_page = lambda self, page: self._has_element(page, "text=Sign In", 3000)
WorkdayFiller._handle_create_account = WorkdayFiller._do_create_account
WorkdayFiller._handle_sign_in = WorkdayFiller._do_sign_in

register_filler(WorkdayFiller)
