"""Tests for Oracle HCM form filler — TDD for Task 5."""
from unittest.mock import MagicMock, call, patch
import pytest

from src.applier.oracle_hcm import OracleHCMFiller
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
    )


def _make_page(inputs=None) -> MagicMock:
    """Create a mock Playwright page."""
    page = MagicMock()
    page.query_selector.return_value = None
    page.query_selector_all.return_value = []
    return page


class TestOracleHCMCanHandle:
    def test_handles_taleo(self):
        filler = OracleHCMFiller(_make_profile())
        assert filler.can_handle("https://jpmc.taleo.net/careersection/10200/jobapply.ftl?job=123")

    def test_handles_oraclecloud(self):
        filler = OracleHCMFiller(_make_profile())
        assert filler.can_handle("https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/apply")

    def test_handles_fa_oraclecloud(self):
        filler = OracleHCMFiller(_make_profile())
        assert filler.can_handle("https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/apply")

    def test_does_not_handle_greenhouse(self):
        filler = OracleHCMFiller(_make_profile())
        assert not filler.can_handle("https://boards.greenhouse.io/company/jobs/123")

    def test_does_not_handle_workday(self):
        filler = OracleHCMFiller(_make_profile())
        assert not filler.can_handle("https://nasdaq.wd1.myworkdayjobs.com/apply")

    def test_platform_name(self):
        filler = OracleHCMFiller(_make_profile())
        assert filler.platform_name() == "oracle_hcm"


class TestOracleHCMFillForm:
    def _make_input_el(self, fill_side_effect=None):
        el = MagicMock()
        el.is_visible.return_value = True
        if fill_side_effect:
            el.fill.side_effect = fill_side_effect
        return el

    def test_fills_first_name(self):
        filler = OracleHCMFiller(_make_profile())
        page = _make_page()

        first_el = self._make_input_el()
        def query_selector_side_effect(sel):
            if "First" in sel or "first" in sel:
                return first_el
            return None
        page.query_selector.side_effect = query_selector_side_effect

        filler.fill_form(page)
        first_el.fill.assert_called_with("Srini")

    def test_fills_last_name(self):
        filler = OracleHCMFiller(_make_profile())
        page = _make_page()

        last_el = self._make_input_el()
        def query_selector_side_effect(sel):
            if "Last" in sel or "last" in sel:
                return last_el
            return None
        page.query_selector.side_effect = query_selector_side_effect

        filler.fill_form(page)
        last_el.fill.assert_called_with("Ravi")

    def test_fills_email(self):
        filler = OracleHCMFiller(_make_profile())
        page = _make_page()

        email_el = self._make_input_el()
        def query_selector_side_effect(sel):
            if "Email" in sel or "email" in sel:
                return email_el
            return None
        page.query_selector.side_effect = query_selector_side_effect

        filler.fill_form(page)
        email_el.fill.assert_called_with("srini@example.com")

    def test_result_includes_filled_fields(self):
        filler = OracleHCMFiller(_make_profile())
        page = _make_page()

        el = self._make_input_el()
        page.query_selector.return_value = el

        result = filler.fill_form(page)
        assert isinstance(result, FillResult)
        assert len(result.fields_filled) > 0

    def test_skips_missing_fields(self):
        filler = OracleHCMFiller(_make_profile())
        page = _make_page()
        # All query_selector returns None — no fields found
        page.query_selector.return_value = None

        result = filler.fill_form(page)
        assert len(result.fields_skipped) > 0

    def test_uploads_resume_when_file_input_found(self):
        filler = OracleHCMFiller(_make_profile())
        page = _make_page()

        file_el = self._make_input_el()
        def query_selector_side_effect(sel):
            if "file" in sel:
                return file_el
            return None
        page.query_selector.side_effect = query_selector_side_effect

        filler.fill_form(page)
        page.set_input_files.assert_called_with("input[type='file']", "config/resumes/resume.pdf")  # resume_path_hint

    def test_no_resume_upload_when_no_file_input(self):
        filler = OracleHCMFiller(_make_profile())
        page = _make_page()
        page.query_selector.return_value = None

        filler.fill_form(page)
        page.set_input_files.assert_not_called()


class TestOracleHCMNavigation:
    def test_navigate_clicks_apply_button(self):
        filler = OracleHCMFiller(_make_profile())
        page = _make_page()

        apply_btn = MagicMock()
        apply_btn.is_visible.return_value = True

        def query_selector_side_effect(sel):
            if "Apply" in sel:
                return apply_btn
            return None
        page.query_selector.side_effect = query_selector_side_effect

        filler._navigate_to_form(page)
        apply_btn.click.assert_called()

    def test_navigate_clicks_guest_apply(self):
        filler = OracleHCMFiller(_make_profile())
        page = _make_page()

        apply_btn = MagicMock()
        apply_btn.is_visible.return_value = True
        guest_btn = MagicMock()
        guest_btn.is_visible.return_value = True

        call_count = [0]
        def query_selector_side_effect(sel):
            if "Guest" in sel or "without signing" in sel or "without an Account" in sel:
                return guest_btn
            if "Apply" in sel:
                call_count[0] += 1
                return apply_btn if call_count[0] <= 1 else None
            return None
        page.query_selector.side_effect = query_selector_side_effect

        result = filler._navigate_to_form(page)
        assert result is True
        guest_btn.click.assert_called_once()

    def test_navigate_returns_true_when_no_guest_prompt(self):
        filler = OracleHCMFiller(_make_profile())
        page = _make_page()
        page.query_selector.return_value = None

        result = filler._navigate_to_form(page)
        assert result is True

    def test_fill_form_calls_navigate_first(self):
        filler = OracleHCMFiller(_make_profile())
        page = _make_page()
        page.query_selector.return_value = None

        with patch.object(filler, '_navigate_to_form', return_value=True) as mock_nav:
            filler.fill_form(page)
            mock_nav.assert_called_once_with(page)


class TestOracleHCMSubmit:
    def test_clicks_submit_button(self):
        filler = OracleHCMFiller(_make_profile())
        page = _make_page()

        submit_el = MagicMock()
        submit_el.is_visible.return_value = True
        page.query_selector.return_value = submit_el

        result = filler.submit(page)
        assert result is True

    def test_returns_false_when_no_submit_button(self):
        filler = OracleHCMFiller(_make_profile())
        page = _make_page()
        page.query_selector.return_value = None

        result = filler.submit(page)
        assert result is False
