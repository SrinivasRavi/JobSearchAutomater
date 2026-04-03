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
        custom_answers={"gender": "Prefer not to say", "veteran_status": "No"},
    )


def _make_page() -> MagicMock:
    page = MagicMock()
    page.query_selector.return_value = None
    page.query_selector_all.return_value = []
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


class TestWorkdayFillForm:
    def _make_input_el(self):
        el = MagicMock()
        el.is_visible.return_value = True
        return el

    def test_returns_fill_result(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()
        result = filler.fill_form(page)
        assert isinstance(result, FillResult)

    def test_fills_first_name_field(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        first_el = self._make_input_el()
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

        last_el = self._make_input_el()
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

        email_el = self._make_input_el()
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

        file_el = self._make_input_el()
        def query_selector_side_effect(sel):
            if "file" in sel:
                return file_el
            return None
        page.query_selector.side_effect = query_selector_side_effect

        filler.fill_form(page)
        page.set_input_files.assert_called_with("input[type='file']", "config/resumes/resume.pdf")  # resume_path_hint

    def test_skips_missing_fields(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()
        page.query_selector.return_value = None

        result = filler.fill_form(page)
        assert len(result.fields_skipped) > 0

    def test_result_success_when_some_filled(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        el = self._make_input_el()
        page.query_selector.return_value = el

        result = filler.fill_form(page)
        assert result.success is True


class TestWorkdayNavigation:
    def test_navigate_clicks_apply_button(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        apply_btn = MagicMock()
        apply_btn.is_visible.return_value = True

        def query_selector_side_effect(sel):
            if "jobPostingApplyButton" in sel:
                return apply_btn
            return None
        page.query_selector.side_effect = query_selector_side_effect

        filler._navigate_to_form(page)
        apply_btn.click.assert_called_once()

    def test_navigate_clicks_apply_manually(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        apply_btn = MagicMock()
        apply_btn.is_visible.return_value = True
        manual_btn = MagicMock()
        manual_btn.is_visible.return_value = True

        call_count = [0]
        def query_selector_side_effect(sel):
            if "Apply Manually" in sel or "Apply manually" in sel:
                return manual_btn
            if "Apply" in sel:
                call_count[0] += 1
                return apply_btn if call_count[0] <= 1 else None
            return None
        page.query_selector.side_effect = query_selector_side_effect

        result = filler._navigate_to_form(page)
        assert result is True
        manual_btn.click.assert_called_once()

    def test_navigate_returns_true_when_no_modal(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()
        page.query_selector.return_value = None

        result = filler._navigate_to_form(page)
        assert result is True

    def test_fill_form_calls_navigate_first(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()
        page.query_selector.return_value = None

        with patch.object(filler, '_navigate_to_form', return_value=True) as mock_nav:
            filler.fill_form(page)
            mock_nav.assert_called_once_with(page)


class TestWorkdaySubmit:
    def test_clicks_next_or_submit_button(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()

        btn = MagicMock()
        btn.is_visible.return_value = True
        page.query_selector.return_value = btn

        result = filler.submit(page)
        assert result is True

    def test_returns_false_when_no_button(self):
        filler = WorkdayFiller(_make_profile())
        page = _make_page()
        page.query_selector.return_value = None

        result = filler.submit(page)
        assert result is False
