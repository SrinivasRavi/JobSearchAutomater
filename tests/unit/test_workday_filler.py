"""Tests for Workday form filler — TDD for Task 6."""
from unittest.mock import MagicMock, patch
import pytest

from src.applier.workday import WorkdayFiller
from src.applier.base import FillResult
from src.models.user_profile import UserProfile


def _make_profile() -> UserProfile:
    return UserProfile(
        profile_id="backend_mumbai",
        profile_name="backend",
        first_name="Srini",
        last_name="Ravi",
        full_name="Srini Ravi",
        email="srini@example.com",
        phone="+91-9876543210",
        city="Mumbai",
        state="Maharashtra",
        country="India",
        zip_code="400001",
        resume_path_hint="config/resumes/resume.pdf",
        ats_password="TestPass123!",
        custom_answers={"gender": "Prefer not to say", "veteran_status": "No"},
    )


def _make_page() -> MagicMock:
    """Create a mock page where all selectors return None by default."""
    page = MagicMock()
    page.query_selector.return_value = None
    page.query_selector_all.return_value = []
    # wait_for_selector raises TimeoutError by default (element not found)
    page.wait_for_selector.side_effect = TimeoutError("not found")
    page.url = "https://nasdaq.wd1.myworkdayjobs.com/apply/123"
    return page


def _make_visible_el():
    """Create a mock element that reports visible."""
    el = MagicMock()
    el.is_visible.return_value = True
    return el


class TestWorkdayCanHandle:
    def test_handles_myworkdayjobs(self):
        filler = WorkdayFiller(_make_profile())
        assert filler.can_handle("https://nasdaq.wd1.myworkdayjobs.com/en-US/ExternalCareers/apply")

    def test_handles_workday_com(self):
        filler = WorkdayFiller(_make_profile())
        assert filler.can_handle("https://acme.workday.com/apply")

    def test_does_not_handle_taleo(self):
        filler = WorkdayFiller(_make_profile())
        assert not filler.can_handle("https://jpmc.taleo.net/careersection/apply")

    def test_does_not_handle_greenhouse(self):
        filler = WorkdayFiller(_make_profile())
        assert not filler.can_handle("https://boards.greenhouse.io/company/jobs/123")

    def test_platform_name(self):
        filler = WorkdayFiller(_make_profile())
        assert filler.platform_name() == "workday"


class TestWorkdayFillForm:
    def test_returns_fill_result(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()
        result = filler.fill_form(page)
        assert isinstance(result, FillResult)

    def test_fills_first_name_field(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        first_el = _make_visible_el()
        def query_selector_side_effect(sel):
            if "legalNameSection_firstName" in sel or "firstName" in sel.lower():
                return first_el
            return None
        page.query_selector.side_effect = query_selector_side_effect

        filler.fill_form(page)
        first_el.fill.assert_called_with("Srini")

    def test_fills_last_name_field(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        last_el = _make_visible_el()
        def query_selector_side_effect(sel):
            if "legalNameSection_lastName" in sel or "lastName" in sel.lower():
                return last_el
            return None
        page.query_selector.side_effect = query_selector_side_effect

        filler.fill_form(page)
        last_el.fill.assert_called_with("Ravi")

    def test_fills_email_field(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        email_el = _make_visible_el()
        def query_selector_side_effect(sel):
            if "email" in sel.lower():
                return email_el
            return None
        page.query_selector.side_effect = query_selector_side_effect

        filler.fill_form(page)
        email_el.fill.assert_called_with("srini@example.com")

    def test_uploads_resume_when_file_input_present(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        file_el = _make_visible_el()
        def query_selector_side_effect(sel):
            if "file" in sel:
                return file_el
            return None
        page.query_selector.side_effect = query_selector_side_effect

        filler.fill_form(page)
        page.set_input_files.assert_called_with("input[type='file']", "config/resumes/resume.pdf")

    def test_skips_missing_fields(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()
        result = filler.fill_form(page)
        assert len(result.fields_skipped) > 0

    def test_result_success_when_some_filled(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        el = _make_visible_el()
        page.query_selector.return_value = el

        result = filler.fill_form(page)
        assert result.success is True


class TestWorkdayNavigation:
    def test_navigate_waits_for_apply_button(self):
        """Apply button found via wait_for_selector."""
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        apply_btn = _make_visible_el()

        def wait_for_selector_side_effect(sel, **kwargs):
            if "jobPostingApplyButton" in sel:
                return apply_btn
            raise TimeoutError("not found")
        page.wait_for_selector.side_effect = wait_for_selector_side_effect

        filler._navigate_to_form(page)
        apply_btn.click.assert_called_once()

    def test_navigate_waits_for_apply_manually(self):
        """After clicking Apply, waits for Apply Manually in modal."""
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        apply_btn = _make_visible_el()
        manual_btn = _make_visible_el()

        def wait_for_selector_side_effect(sel, **kwargs):
            if "jobPostingApplyButton" in sel:
                return apply_btn
            if "Apply Manually" in sel:
                return manual_btn
            raise TimeoutError("not found")
        page.wait_for_selector.side_effect = wait_for_selector_side_effect

        result = filler._navigate_to_form(page)
        assert result is True
        apply_btn.click.assert_called_once()
        manual_btn.click.assert_called_once()

    def test_navigate_returns_false_when_no_apply_button(self):
        """If Apply button never appears, returns False."""
        filler = WorkdayFiller(_make_profile())
        page = _make_page()
        # All wait_for_selector raise TimeoutError (default)

        result = filler._navigate_to_form(page)
        assert result is False

    def test_fill_form_calls_navigate_first(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        with patch.object(filler, '_navigate_to_form', return_value=True) as mock_nav:
            filler.fill_form(page)
            mock_nav.assert_called_once_with(page)


class TestWorkdayAccountCreation:
    def _make_create_account_page(self):
        """Mock a page that shows Create Account form."""
        page = _make_page()

        create_heading = _make_visible_el()
        create_btn = _make_visible_el()
        checkbox = _make_visible_el()
        checkbox.is_checked.return_value = False
        email_el = _make_visible_el()

        password_input_1 = _make_visible_el()
        password_input_2 = _make_visible_el()
        page.query_selector_all.return_value = [password_input_1, password_input_2]

        def wait_for_selector_side_effect(sel, **kwargs):
            if "Create Account" in sel and ("h2" in sel or "h1" in sel):
                return create_heading
            if "Create Account" in sel and "button" in sel.lower():
                return create_btn
            if "createAccountSubmitButton" in sel:
                return create_btn
            if "email" in sel.lower() or "Email" in sel:
                return email_el
            raise TimeoutError("not found")
        page.wait_for_selector.side_effect = wait_for_selector_side_effect

        def query_selector_side_effect(sel):
            if "checkbox" in sel:
                return checkbox
            return None
        page.query_selector.side_effect = query_selector_side_effect

        return page, create_btn, checkbox, email_el, password_input_1, password_input_2

    def test_detects_create_account_page(self):
        filler = WorkdayFiller(_make_profile())
        page, *_ = self._make_create_account_page()
        assert filler._is_create_account_page(page) is True

    def test_does_not_detect_create_account_on_normal_page(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()
        # All wait_for_selector raise TimeoutError (default)
        assert filler._is_create_account_page(page) is False

    def test_fills_email_on_create_account(self):
        filler = WorkdayFiller(_make_profile())
        page, _, _, email_el, _, _ = self._make_create_account_page()
        filler._handle_create_account(page)
        email_el.fill.assert_called_with("srini@example.com")

    def test_fills_both_password_fields(self):
        filler = WorkdayFiller(_make_profile())
        page, _, _, _, pw1, pw2 = self._make_create_account_page()
        filler._handle_create_account(page)
        pw1.fill.assert_called_with("TestPass123!")
        pw2.fill.assert_called_with("TestPass123!")

    def test_checks_consent_checkbox(self):
        filler = WorkdayFiller(_make_profile())
        page, _, checkbox, _, _, _ = self._make_create_account_page()
        filler._handle_create_account(page)
        checkbox.click.assert_called_once()

    def test_clicks_create_account_button(self):
        filler = WorkdayFiller(_make_profile())
        page, create_btn, _, _, _, _ = self._make_create_account_page()
        filler._handle_create_account(page)
        create_btn.click.assert_called()

    def test_navigate_handles_create_account_flow(self):
        """Full navigation: Apply → modal → Create Account."""
        filler = WorkdayFiller(_make_profile())
        page, *_ = self._make_create_account_page()

        with patch.object(filler, '_handle_create_account') as mock_create:
            with patch.object(filler, '_is_create_account_page', return_value=True):
                # Make Apply button found so we don't return False early
                apply_btn = _make_visible_el()
                original_side_effect = page.wait_for_selector.side_effect
                def patched_wait(sel, **kwargs):
                    if "jobPostingApplyButton" in sel:
                        return apply_btn
                    if "Apply Manually" in sel:
                        return _make_visible_el()
                    return original_side_effect(sel, **kwargs)
                page.wait_for_selector.side_effect = patched_wait

                result = filler._navigate_to_form(page)
                assert result is True
                mock_create.assert_called_once_with(page)


class TestWorkdaySubmit:
    def test_clicks_next_or_submit_button(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        btn = _make_visible_el()
        page.query_selector.return_value = btn

        result = filler.submit(page)
        assert result is True

    def test_returns_false_when_no_button(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()
        page.query_selector.return_value = None

        result = filler.submit(page)
        assert result is False
