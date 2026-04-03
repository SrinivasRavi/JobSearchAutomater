"""Tests for Workday form filler."""
from unittest.mock import MagicMock, patch, PropertyMock
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
    """Create a mock Playwright page.

    By default:
    - locator().first.wait_for() raises Exception (element not found)
    - locator().first.is_visible() returns False
    - locator().count() returns 0
    - query_selector returns None
    """
    page = MagicMock()
    page.query_selector.return_value = None
    page.query_selector_all.return_value = []

    # Default locator behavior: not found
    mock_locator = MagicMock()
    mock_locator.first.wait_for.side_effect = Exception("Timeout")
    mock_locator.first.is_visible.return_value = False
    mock_locator.count.return_value = 0
    mock_locator.nth.return_value = MagicMock()
    page.locator.return_value = mock_locator

    page.url = "https://nasdaq.wd1.myworkdayjobs.com/apply/123"
    return page


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


class TestWorkdayClick:
    def test_click_uses_force_true(self):
        """Verify that force=True is passed to click (bypasses Workday overlay)."""
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        mock_locator = MagicMock()
        mock_locator.first.wait_for.return_value = None  # Element found
        page.locator.return_value = mock_locator

        filler._click(page, "button:has-text('Apply')", "test button")
        mock_locator.first.click.assert_called_once_with(force=True, timeout=5000)

    def test_click_returns_false_on_timeout(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()
        # Default mock raises Exception on wait_for
        assert filler._click(page, "button:has-text('Apply')", "test") is False

    def test_click_any_tries_selectors_in_order(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        call_count = [0]
        def locator_side_effect(sel):
            call_count[0] += 1
            mock = MagicMock()
            if call_count[0] == 2:  # Second selector succeeds
                mock.first.wait_for.return_value = None
            else:
                mock.first.wait_for.side_effect = Exception("Timeout")
            return mock
        page.locator.side_effect = locator_side_effect

        result = filler._click_any(page, ["sel1", "sel2", "sel3"], "test")
        assert result is True
        assert call_count[0] == 2  # Stopped after finding second


class TestWorkdayNavigation:
    def test_navigate_returns_false_when_no_apply_button(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()
        result = filler._navigate_to_form(page)
        assert result is False

    def test_navigate_clicks_apply_then_modal(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        clicks = []
        def locator_side_effect(sel):
            mock = MagicMock()
            if "Apply" in sel:
                mock.first.wait_for.return_value = None
                def record_click(**kwargs):
                    clicks.append(sel)
                mock.first.click.side_effect = record_click
            else:
                mock.first.wait_for.side_effect = Exception("Timeout")
            mock.count.return_value = 0
            mock.first.is_visible.return_value = False
            return mock
        page.locator.side_effect = locator_side_effect

        filler._navigate_to_form(page)
        assert len(clicks) >= 1  # At least Apply button was clicked

    def test_fill_form_calls_navigate(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        with patch.object(filler, '_navigate_to_form', return_value=True) as mock_nav:
            filler.fill_form(page)
            mock_nav.assert_called_once_with(page)


class TestWorkdayAccountCreation:
    def test_detects_create_account_page(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        def locator_side_effect(sel):
            mock = MagicMock()
            if "Create Account" in sel:
                mock.first.wait_for.return_value = None
            else:
                mock.first.wait_for.side_effect = Exception("Timeout")
            return mock
        page.locator.side_effect = locator_side_effect

        assert filler._is_create_account_page(page) is True

    def test_does_not_detect_on_normal_page(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()
        # Default mock raises on wait_for
        assert filler._is_create_account_page(page) is False

    def test_fills_email_on_create_account(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        filled_values = {}
        def locator_side_effect(sel):
            mock = MagicMock()
            if "email" in sel.lower() or "Email" in sel:
                mock.first.wait_for.return_value = None
                mock.first.fill.side_effect = lambda v: filled_values.update({"email": v})
            else:
                mock.first.wait_for.side_effect = Exception("Timeout")
            # Password inputs
            mock.count.return_value = 2
            pw_mock = MagicMock()
            mock.nth.return_value = pw_mock
            # Checkbox
            mock.first.is_visible.return_value = False
            mock.first.is_checked.return_value = False
            return mock
        page.locator.side_effect = locator_side_effect

        filler._handle_create_account(page)
        assert filled_values.get("email") == "srini@example.com"

    def test_fills_password_fields(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        pw_values = []
        pw_mock_0 = MagicMock()
        pw_mock_0.fill.side_effect = lambda v: pw_values.append(("pw0", v))
        pw_mock_1 = MagicMock()
        pw_mock_1.fill.side_effect = lambda v: pw_values.append(("pw1", v))

        def locator_side_effect(sel):
            mock = MagicMock()
            mock.first.wait_for.side_effect = Exception("Timeout")
            mock.first.is_visible.return_value = False
            mock.first.is_checked.return_value = False
            if sel == "input[type='password']":
                mock.count.return_value = 2
                def nth_side_effect(idx):
                    return pw_mock_0 if idx == 0 else pw_mock_1
                mock.nth.side_effect = nth_side_effect
            else:
                mock.count.return_value = 0
            return mock
        page.locator.side_effect = locator_side_effect

        filler._handle_create_account(page)
        assert ("pw0", "TestPass123!") in pw_values
        assert ("pw1", "TestPass123!") in pw_values

    def test_navigate_calls_create_account_handler(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        with patch.object(filler, '_click_any', return_value=True):
            with patch.object(filler, '_is_create_account_page', return_value=True):
                with patch.object(filler, '_handle_create_account') as mock_create:
                    with patch.object(filler, '_take_screenshot'):
                        filler._navigate_to_form(page)
                        mock_create.assert_called_once_with(page)


class TestWorkdayFillForm:
    def test_returns_fill_result(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        with patch.object(filler, '_navigate_to_form', return_value=True):
            with patch.object(filler, '_take_screenshot'):
                result = filler.fill_form(page)
                assert isinstance(result, FillResult)

    def test_fills_visible_fields(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        filled_fields = {}
        def locator_side_effect(sel):
            mock = MagicMock()
            if "legalNameSection_firstName" in sel:
                mock.first.is_visible.return_value = True
                mock.first.fill.side_effect = lambda v: filled_fields.update({"first_name": v})
            elif "legalNameSection_lastName" in sel:
                mock.first.is_visible.return_value = True
                mock.first.fill.side_effect = lambda v: filled_fields.update({"last_name": v})
            else:
                mock.first.is_visible.return_value = False
            mock.count.return_value = 0
            return mock
        page.locator.side_effect = locator_side_effect

        with patch.object(filler, '_navigate_to_form', return_value=True):
            with patch.object(filler, '_take_screenshot'):
                result = filler.fill_form(page)
                assert "first_name" in result.fields_filled
                assert filled_fields["first_name"] == "Srini"
                assert filled_fields["last_name"] == "Ravi"

    def test_skips_invisible_fields(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        with patch.object(filler, '_navigate_to_form', return_value=True):
            with patch.object(filler, '_take_screenshot'):
                result = filler.fill_form(page)
                assert len(result.fields_skipped) > 0


class TestWorkdaySubmit:
    def test_clicks_submit_button(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        def locator_side_effect(sel):
            mock = MagicMock()
            if "Save and Continue" in sel:
                mock.first.wait_for.return_value = None
            else:
                mock.first.wait_for.side_effect = Exception("Timeout")
            return mock
        page.locator.side_effect = locator_side_effect

        assert filler.submit(page) is True

    def test_returns_false_when_no_button(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()
        assert filler.submit(page) is False
