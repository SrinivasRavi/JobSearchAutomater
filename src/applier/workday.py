"""Workday form filler — handles Nasdaq and other Workday ATS instances.

Flow:
1. Job detail page → click "Apply" button
2. "Start Your Application" modal → click "Apply Manually" (if present)
3. Account page → Sign In (preferred) or Create Account
4. Fill ALL wizard pages: My Information → My Experience → Application Questions
   → Voluntary Disclosures → Review
5. Screenshot before each page fill for diagnosis

Key Workday quirk: ALL buttons are wrapped in a <div data-automation-id="click_filter">
overlay that intercepts pointer events. We must use force=True on all clicks.
"""
import logging
import os
import re

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

# Form field selectors — discovered via real Nasdaq DOM inspection.
# Workday My Information page uses name= and id= attributes.
_FIELD_SELECTORS = [
    ("first_name", "input[id='name--legalName--firstName']"),
    ("first_name", "input[name='legalName--firstName']"),
    ("first_name", "[data-automation-id='legalNameSection_firstName']"),
    ("last_name", "input[id='name--legalName--lastName']"),
    ("last_name", "input[name='legalName--lastName']"),
    ("last_name", "[data-automation-id='legalNameSection_lastName']"),
    ("phone", "input[id='phoneNumber--phoneNumber']"),
    ("phone", "input[name='phoneNumber']"),
    ("phone", "[data-automation-id='phone-number']"),
    ("city", "input[id='address--city']"),
    ("city", "input[name='city']"),
    ("city", "[data-automation-id='addressSection_city']"),
    ("zip_code", "input[id='address--postalCode']"),
    ("zip_code", "input[name='postalCode']"),
    ("zip_code", "[data-automation-id='addressSection_postalCode']"),
    ("email", "[data-automation-id='email']"),
    ("email", "input[aria-label*='Email']"),
]

_SAVE_CONTINUE_SELECTORS = [
    "button:has-text('Save and Continue')",
    "button[data-automation-id='bottom-navigation-next-button']",
    "button:has-text('Next')",
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
            print(f"  [fill]  {description} = {value[:40]}")
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

    def _has_element(self, page, selector: str, timeout: int = 3000) -> bool:
        try:
            page.locator(selector).first.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    def _scroll_full_page(self, page) -> None:
        """Scroll through entire page to trigger lazy loading."""
        for pos in [500, 1000, 1500, 2000, 3000]:
            page.evaluate(f"window.scrollTo(0, {pos})")
            page.wait_for_timeout(300)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

    @staticmethod
    def _strip_country_code(phone: str) -> str:
        """Strip country code prefix for Workday's split phone input.
        +917208816364 → 7208816364
        +91-7208816364 → 7208816364
        917208816364 → 7208816364
        7208816364 → 7208816364
        """
        # Remove leading + if present
        p = phone.lstrip('+')
        # Remove common country codes (91 for India, 1 for US) only if followed by 10 digits
        match = re.match(r'^(91|1)(\d{10})$', p)
        if match:
            return match.group(2)
        # Remove country code with separator
        match = re.match(r'^(?:\+?91|1)[-\s](.+)$', phone)
        if match:
            return match.group(1)
        return p

    # --- Navigation ---

    def _navigate_to_form(self, page) -> bool:
        """Navigate: Apply → modal → Sign In → form page."""

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
            self._wait_and_screenshot(page, "no_modal", 3000)

        # Step 3: Sign In or Create Account
        print("  Step 3: Sign In or Create Account")
        self._handle_account(page)

        return True

    def _handle_account(self, page) -> None:
        """Handle the account page. Detect by password field count."""
        page.wait_for_timeout(2000)

        try:
            pw_count = page.locator("input[type='password']").count()
        except Exception:
            pw_count = 0

        print(f"  Password fields found: {pw_count}")

        if pw_count == 1:
            print("  Sign In page (1 password field)")
            self._do_sign_in(page)
        elif pw_count >= 2:
            print("  Create Account page (2+ password fields) — switching to Sign In")
            sign_in_clicked = False
            for sel in _SIGN_IN_LINK_SELECTORS:
                if self._click(page, sel, "Sign In link", timeout=3000):
                    sign_in_clicked = True
                    break
            if sign_in_clicked:
                self._wait_and_screenshot(page, "switched_to_sign_in", 3000)
                self._do_sign_in(page)
            else:
                print("  No Sign In link — creating new account")
                self._do_create_account(page)
        elif self._has_sign_in_modal(page):
            print("  Sign In modal detected")
            self._do_sign_in(page)
        else:
            print("  No account page — may already be on form")
            self._take_screenshot(page, "no_account_page")

    def _has_sign_in_modal(self, page) -> bool:
        try:
            page.locator("[role='dialog']:has-text('Sign In')").first.wait_for(
                state="visible", timeout=3000
            )
            return True
        except Exception:
            return False

    def _do_sign_in(self, page) -> None:
        """Fill and submit Sign In form, scoped to modal if present."""
        profile = self.profile

        # Scope to modal if present
        modal = None
        try:
            modal_loc = page.locator("[role='dialog']").first
            modal_loc.wait_for(state="visible", timeout=3000)
            modal = modal_loc
            print("  Sign In modal — scoping selectors")
        except Exception:
            pass

        scope = modal if modal else page

        # Fill email
        for sel in [
            "input[data-automation-id='email']",
            "[data-automation-id='signInEmailAddress']",
            "input[aria-label*='Email']",
            "input[type='email']",
            "input[type='text']",
        ]:
            try:
                loc = scope.locator(sel).first
                loc.wait_for(state="visible", timeout=3000)
                loc.fill(profile.email)
                print(f"  [fill]  sign-in email = {profile.email}")
                break
            except Exception:
                continue

        # Fill password
        if profile.ats_password:
            try:
                pw = scope.locator("input[type='password']").first
                pw.wait_for(state="visible", timeout=3000)
                pw.fill(profile.ats_password)
                print("  [fill]  sign-in password")
            except Exception:
                print("  [miss]  password field not found")

        self._take_screenshot(page, "sign_in_filled")

        # Click Sign In
        for sel in _SIGN_IN_BUTTON_SELECTORS:
            try:
                btn = scope.locator(sel).first
                btn.wait_for(state="visible", timeout=3000)
                btn.click(force=True, timeout=5000)
                print("  [click] Sign In button")
                self._wait_for_form_page(page, "after_sign_in")
                return
            except Exception:
                continue
        print("  FAILED: Sign In button not found")
        self._take_screenshot(page, "sign_in_failed")

    def _do_create_account(self, page) -> None:
        """Fill and submit Create Account form."""
        profile = self.profile
        self._fill_any(page, _CREATE_ACCOUNT_EMAIL_SELECTORS, profile.email, "account email", timeout=10000)
        page.wait_for_timeout(500)

        if not profile.ats_password:
            print("  FAILED: No ats_password in profile")
            return

        pw_inputs = page.locator("input[type='password']")
        count = pw_inputs.count()
        if count >= 2:
            pw_inputs.nth(0).fill(profile.ats_password)
            page.wait_for_timeout(300)
            pw_inputs.nth(1).fill(profile.ats_password)
            print("  [fill]  password x2")
        elif count == 1:
            pw_inputs.nth(0).fill(profile.ats_password)
            print("  [fill]  password x1")

        try:
            cb = page.locator("input[type='checkbox']").first
            if cb.is_visible() and not cb.is_checked():
                cb.click(force=True)
                print("  [click] consent checkbox")
        except Exception:
            pass

        self._take_screenshot(page, "before_create_account_click")

        if self._click_any(page, _CREATE_ACCOUNT_BUTTON_SELECTORS, "Create Account", timeout=10000):
            self._wait_for_form_page(page, "after_create_account")
        else:
            print("  FAILED: Create Account button not found")
            self._take_screenshot(page, "create_account_failed")
            if self._has_element(page, "a:has-text('Sign In')", 3000):
                self._click_any(page, _SIGN_IN_LINK_SELECTORS, "Sign In fallback", timeout=5000)
                page.wait_for_timeout(2000)
                self._do_sign_in(page)

    def _wait_for_form_page(self, page, label: str) -> None:
        """Wait for a form page to load after sign-in or account creation."""
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(3000)

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

        # Sign In redirect?
        if self._has_element(page, "text=Sign In", 2000):
            print("  Redirected to Sign In")
            self._take_screenshot(page, "redirected_sign_in")
            self._do_sign_in(page)
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

        print("  WARNING: Unknown page state")
        self._take_screenshot(page, label + "_unknown")

    # --- Form filling (multi-page) ---

    def fill_form(self, page) -> FillResult:
        self._navigate_to_form(page)

        all_filled: list[str] = []
        all_skipped: list[str] = []

        # Fill all wizard pages until we hit Review or run out of pages
        max_pages = 7
        for page_num in range(1, max_pages + 1):
            print(f"\n  === Wizard Page {page_num} ===")

            # Screenshot BEFORE filling — see what we're working with
            self._scroll_full_page(page)
            self._take_screenshot(page, f"page_{page_num}_before_fill")

            # Detect page type and fill accordingly
            page_title = self._get_page_title(page)
            print(f"  Page title: {page_title}")

            if "review" in page_title.lower():
                print("  Reached Review page — stopping auto-fill")
                break

            filled, skipped = self._fill_current_page(page, page_title)
            all_filled.extend(filled)
            all_skipped.extend(skipped)

            self._take_screenshot(page, f"page_{page_num}_after_fill")

            # Click Save and Continue
            if not self._click_save_continue(page):
                print("  No Save and Continue button — stopping")
                break

            # Wait for next page to load
            self._wait_for_page_transition(page)

        return FillResult(
            success=len(all_filled) > 0,
            fields_filled=all_filled,
            fields_skipped=all_skipped,
        )

    def _get_page_title(self, page) -> str:
        """Get the current wizard page title (e.g., 'My Information', 'My Experience')."""
        # Look for the main heading on the page
        for sel in ["h2", "h1"]:
            try:
                headings = page.locator(sel).all()
                for h in headings:
                    text = h.text_content().strip()
                    if text and text not in ("", "Nasdaq") and len(text) < 50:
                        return text
            except Exception:
                pass
        return "Unknown"

    def _fill_current_page(self, page, page_title: str) -> tuple[list[str], list[str]]:
        """Fill fields on whatever page is currently showing."""
        title_lower = page_title.lower()

        if "my information" in title_lower or "information" in title_lower:
            return self._fill_my_information(page)
        elif "my experience" in title_lower or "experience" in title_lower:
            return self._fill_my_experience(page)
        elif "application questions" in title_lower or "question" in title_lower:
            return self._fill_application_questions(page)
        elif "voluntary" in title_lower or "disclosure" in title_lower:
            return self._fill_voluntary_disclosures(page)
        else:
            print(f"  Unknown page type: '{page_title}' — attempting generic fill")
            return self._fill_generic_page(page)

    def _fill_my_information(self, page) -> tuple[list[str], list[str]]:
        """Fill the My Information page."""
        profile = self.profile
        filled: list[str] = []
        skipped: list[str] = []
        seen: set[str] = set()

        field_values = {
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "email": profile.email,
            "phone": self._strip_country_code(profile.phone),
            "city": profile.city,
            "zip_code": profile.zip_code,
        }

        # Fill "How Did You Hear About Us?" dropdown — pick first option
        self._fill_workday_dropdown(page, "input[id='source--source']", "How Did You Hear")

        # Fill radio buttons (e.g., "Previously worked for Nasdaq?")
        self._fill_radio_no(page, "candidateIsPreviousWorker")

        # Fill text fields
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
                    loc.fill(field_values[field_name])
                    filled.append(field_name)
                    seen.add(field_name)
                    print(f"  [fill]  {field_name} = {field_values[field_name]}")
            except Exception:
                pass

        for fn in field_values:
            if fn not in seen:
                skipped.append(fn)

        return filled, skipped

    def _fill_my_experience(self, page) -> tuple[list[str], list[str]]:
        """Fill My Experience page — resume upload."""
        filled: list[str] = []
        skipped: list[str] = []

        # Resume upload
        resume_path = self.profile.resume_path_hint
        if resume_path and os.path.exists(resume_path):
            try:
                file_input = page.locator("input[type='file']")
                if file_input.count() > 0:
                    file_input.first.set_input_files(resume_path)
                    filled.append("resume")
                    print(f"  [fill]  resume = {resume_path}")
                    page.wait_for_timeout(2000)
                else:
                    # Try drag-drop area or button
                    skipped.append("resume")
                    print("  [skip]  resume — no file input found")
            except Exception as e:
                skipped.append("resume")
                print(f"  [skip]  resume — {e}")
        else:
            skipped.append("resume")
            print(f"  [skip]  resume — file not found: {resume_path}")

        return filled, skipped

    def _fill_application_questions(self, page) -> tuple[list[str], list[str]]:
        """Fill Application Questions page using custom_answers from profile."""
        filled: list[str] = []
        skipped: list[str] = []
        profile = self.profile
        custom = getattr(profile, 'custom_answers', {}) or {}

        # Try to fill any visible text inputs with reasonable defaults
        try:
            inputs = page.locator("input[type='text']:visible").all()
            for inp in inputs:
                try:
                    inp_id = inp.get_attribute("id") or ""
                    inp_name = inp.get_attribute("name") or ""
                    label_text = self._get_label_for_input(page, inp)

                    if not label_text:
                        continue

                    value = self._match_custom_answer(label_text, custom, profile)
                    if value:
                        inp.fill(value)
                        filled.append(label_text[:30])
                        print(f"  [fill]  {label_text[:40]} = {value[:30]}")
                except Exception:
                    pass
        except Exception:
            pass

        # Fill any dropdowns
        try:
            selects = page.locator("select:visible").all()
            for sel_elem in selects:
                try:
                    # Select first non-empty option
                    options = sel_elem.locator("option").all()
                    for opt in options[1:]:  # Skip first (usually "Select...")
                        val = opt.get_attribute("value")
                        if val:
                            sel_elem.select_option(value=val)
                            print(f"  [fill]  dropdown = {opt.text_content()[:30]}")
                            break
                except Exception:
                    pass
        except Exception:
            pass

        # Fill radio buttons — try to select "No" or "Prefer not to say" where available
        self._fill_all_radios_default(page)

        return filled, skipped

    def _fill_voluntary_disclosures(self, page) -> tuple[list[str], list[str]]:
        """Fill Voluntary Disclosures page with 'Prefer not to say' where possible."""
        filled: list[str] = []
        custom = getattr(self.profile, 'custom_answers', {}) or {}

        # Fill dropdowns with "Prefer not to say" or first option
        self._fill_all_workday_dropdowns_default(page)

        # Fill radio buttons
        self._fill_all_radios_default(page)

        return filled, []

    def _fill_generic_page(self, page) -> tuple[list[str], list[str]]:
        """Generic fill — try text fields, radios, dropdowns."""
        self._fill_all_radios_default(page)
        self._fill_all_workday_dropdowns_default(page)
        return [], []

    # --- Workday custom dropdown handling ---

    def _fill_workday_dropdown(self, page, input_selector: str, description: str) -> bool:
        """Fill a Workday custom dropdown (not a <select>).

        Workday dropdowns: click the input → options list appears → click first option.
        """
        try:
            inp = page.locator(input_selector).first
            inp.scroll_into_view_if_needed(timeout=2000)
            if not inp.is_visible():
                return False

            # Click to open dropdown
            inp.click(force=True)
            page.wait_for_timeout(1000)

            # Wait for dropdown options to appear
            # Workday renders options in a popup/list
            option_selectors = [
                "[role='listbox'] [role='option']",
                "[data-automation-id='promptOption']",
                "[role='option']",
                "li[role='option']",
            ]
            for opt_sel in option_selectors:
                try:
                    first_opt = page.locator(opt_sel).first
                    first_opt.wait_for(state="visible", timeout=3000)
                    option_text = first_opt.text_content().strip()
                    first_opt.click(force=True)
                    print(f"  [fill]  {description} = {option_text[:40]}")
                    page.wait_for_timeout(500)

                    # Some Workday dropdowns have a second level
                    # Check if another dropdown appeared
                    page.wait_for_timeout(1000)
                    try:
                        sub_opt = page.locator(opt_sel).first
                        sub_opt.wait_for(state="visible", timeout=2000)
                        sub_text = sub_opt.text_content().strip()
                        sub_opt.click(force=True)
                        print(f"  [fill]  {description} (sub) = {sub_text[:40]}")
                        page.wait_for_timeout(500)
                    except Exception:
                        pass  # No sub-dropdown, that's fine

                    return True
                except Exception:
                    continue

            print(f"  [miss]  {description} dropdown options not found")
            # Close the dropdown by pressing Escape
            inp.press("Escape")
            return False
        except Exception:
            return False

    def _fill_all_workday_dropdowns_default(self, page) -> None:
        """Find and fill all visible Workday custom dropdowns with first option."""
        # Workday custom dropdowns typically have a button/icon next to them
        try:
            # Look for inputs that have dropdown indicators
            dropdowns = page.locator("input[id*='--']:visible").all()
            for dd in dropdowns:
                try:
                    dd_id = dd.get_attribute("id") or ""
                    # Skip known non-dropdown fields
                    if any(skip in dd_id for skip in ["firstName", "lastName", "city", "postal",
                                                       "phone", "address", "email", "extension"]):
                        continue
                    self._fill_workday_dropdown(page, f"input[id='{dd_id}']", dd_id)
                except Exception:
                    pass
        except Exception:
            pass

    # --- Radio button handling ---

    def _fill_radio_no(self, page, name: str) -> None:
        """Click the 'No' radio button for a given radio group."""
        try:
            radios = page.locator(f"input[name='{name}']")
            if radios.count() >= 2:
                no_radio = radios.nth(1)
                if no_radio.is_visible():
                    no_radio.click(force=True)
                    print(f"  [click] radio '{name}' = No")
        except Exception:
            pass

    def _fill_all_radios_default(self, page) -> None:
        """Find all visible radio groups and select a reasonable default."""
        try:
            # Get unique radio group names
            radios = page.locator("input[type='radio']:visible").all()
            seen_names: set[str] = set()
            for radio in radios:
                name = radio.get_attribute("name") or ""
                if name and name not in seen_names:
                    seen_names.add(name)
                    # For most questions, pick last option (often "No" or "Prefer not to say")
                    group = page.locator(f"input[name='{name}']")
                    count = group.count()
                    if count > 0:
                        # Try to find "No" or "Prefer not to say" option
                        last = group.nth(count - 1)
                        if last.is_visible():
                            last.click(force=True)
                            print(f"  [click] radio '{name}' = option {count}")
        except Exception:
            pass

    # --- Helpers ---

    def _get_label_for_input(self, page, inp) -> str:
        """Try to get the label text for an input element."""
        try:
            inp_id = inp.get_attribute("id")
            if inp_id:
                label = page.locator(f"label[for='{inp_id}']").first
                return label.text_content().strip()
        except Exception:
            pass
        return ""

    def _match_custom_answer(self, label: str, custom: dict, profile) -> str:
        """Match a question label to a custom_answers value."""
        label_lower = label.lower()

        if "sponsor" in label_lower:
            return custom.get("sponsorship_required", "No")
        if "authorized" in label_lower or "eligible" in label_lower:
            return custom.get("authorized_to_work", "Yes")
        if "ctc" in label_lower or "salary" in label_lower or "compensation" in label_lower:
            if "current" in label_lower:
                return custom.get("current_ctc", "")
            if "expected" in label_lower:
                return custom.get("expected_ctc", "")
        if "notice" in label_lower:
            days = getattr(profile, 'notice_period_days', 0)
            if hasattr(profile, 'employment') and hasattr(profile.employment, 'notice_period_days'):
                days = profile.employment.notice_period_days
            return str(days) if days else "0"
        if "experience" in label_lower and "year" in label_lower:
            yoe = getattr(profile, 'years_of_experience', "")
            if hasattr(profile, 'employment') and hasattr(profile.employment, 'years_of_experience'):
                yoe = profile.employment.years_of_experience
            return str(yoe) if yoe else ""

        return ""

    def _click_save_continue(self, page) -> bool:
        """Click the Save and Continue / Next button."""
        for sel in _SAVE_CONTINUE_SELECTORS:
            if self._click(page, sel, "Save and Continue", timeout=5000):
                return True
        return False

    def _wait_for_page_transition(self, page) -> None:
        """Wait for Workday to load the next wizard page."""
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(3000)

    def submit(self, page) -> bool:
        for selector in _SUBMIT_SELECTORS:
            if self._click(page, selector, "Submit", timeout=3000):
                return True
        return False


# Backward compat aliases for tests
WorkdayFiller._is_create_account_page = lambda self, page: self._has_element(page, "text=Create Account", 3000)
WorkdayFiller._is_sign_in_page = lambda self, page: self._has_element(page, "text=Sign In", 3000)
WorkdayFiller._handle_create_account = WorkdayFiller._do_create_account
WorkdayFiller._handle_sign_in = WorkdayFiller._do_sign_in

register_filler(WorkdayFiller)
