"""Tests for the apply orchestrator — TDD for Task 4."""
from unittest.mock import MagicMock, patch
import pytest

from src.applier.base import FillResult
from src.applier.orchestrator import ApplyOrchestrator, ApplyResult, check_ats_support
from src.models.user_profile import UserProfile
from src.persistence.database import Database
from src.persistence.repository import ApplicationRepository


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
        resume_path_hint="resume.pdf",
    )


@pytest.fixture
def db():
    d = Database(":memory:")
    d.initialize()
    yield d
    d.close()


@pytest.fixture
def app_repo(db):
    return ApplicationRepository(db.connection)


@pytest.fixture
def profile():
    return _make_profile()


@pytest.fixture
def mock_filler():
    filler = MagicMock()
    filler.platform_name.return_value = "workday"
    filler.fill_form.return_value = FillResult(
        success=True,
        fields_filled=["first_name", "last_name", "email"],
        fields_skipped=["phone"],
    )
    filler.submit.return_value = True
    return filler


class TestCheckAtsSupport:
    def test_returns_none_for_unknown_url(self, profile):
        with patch("src.applier.orchestrator.get_filler_for_url", return_value=None):
            assert check_ats_support("https://greenhouse.io/apply", profile) is None

    def test_returns_filler_for_known_url(self, profile):
        mock = MagicMock()
        with patch("src.applier.orchestrator.get_filler_for_url", return_value=mock):
            result = check_ats_support("https://acme.wd1.myworkdayjobs.com/apply", profile)
            assert result is mock


class TestMarkUnsupported:
    def test_records_failed_application(self, db, app_repo, profile):
        orch = ApplyOrchestrator(db.connection, profile)
        app_id = orch.mark_unsupported(
            job_url="https://greenhouse.io/apply/123",
            job_id=None,
            job_title="SWE",
            company_name="Acme",
        )
        assert app_id > 0
        apps = app_repo.list_applications()
        assert len(apps) == 1
        assert apps[0]["status"] == "FAILED"
        assert apps[0]["failure_reason"] == "UNSUPPORTED_ATS"

    def test_stores_profile_id(self, db, app_repo, profile):
        orch = ApplyOrchestrator(db.connection, profile)
        orch.mark_unsupported(job_url="https://x.com", job_title="SWE", company_name="X")
        apps = app_repo.list_applications()
        assert apps[0]["profile_name"] == "backend_mumbai"  # profile_id, not profile_name


class TestApplyWithFiller:
    def _run_with_answer(self, answer, db, profile, mock_filler):
        """Run the orchestrator with a mocked filler and user input."""
        orch = ApplyOrchestrator(db.connection, profile)
        mock_page = MagicMock()
        mock_page.url = "https://acme.wd1.myworkdayjobs.com/apply/42"

        with patch("src.applier.orchestrator.sync_playwright") as mock_pw, \
             patch("builtins.input", return_value=answer), \
             patch("os.makedirs"):
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_browser.new_context.return_value.__enter__ = MagicMock(return_value=mock_context)
            mock_browser.new_context.return_value.__exit__ = MagicMock(return_value=False)
            mock_context.new_page.return_value = mock_page
            mock_pw.return_value.__enter__ = MagicMock(return_value=MagicMock(
                chromium=MagicMock(
                    launch=MagicMock(return_value=mock_browser)
                )
            ))
            mock_pw.return_value.__exit__ = MagicMock(return_value=False)

            result = orch.apply_with_filler(
                filler=mock_filler,
                job_url="https://acme.wd1.myworkdayjobs.com/apply/42",
                job_id=None,
                job_title="Backend Engineer",
                company_name="Acme",
            )
        return result

    def test_submit_on_yes(self, db, profile, mock_filler):
        result = self._run_with_answer("y", db, profile, mock_filler)
        assert result.status == "SUBMITTED"
        mock_filler.submit.assert_called_once()

    def test_fail_on_no(self, db, profile, mock_filler):
        result = self._run_with_answer("n", db, profile, mock_filler)
        assert result.status == "FAILED"
        assert result.failure_reason == "HUMAN_REJECTED"
        mock_filler.submit.assert_not_called()

    def test_skip_on_skip(self, db, profile, mock_filler):
        result = self._run_with_answer("skip", db, profile, mock_filler)
        assert result.status == "SKIPPED"
        mock_filler.submit.assert_not_called()

    def test_records_application_on_submit(self, db, profile, mock_filler):
        self._run_with_answer("y", db, profile, mock_filler)
        app_repo = ApplicationRepository(db.connection)
        apps = app_repo.list_applications()
        assert len(apps) == 1
        assert apps[0]["status"] == "SUBMITTED"
        assert apps[0]["profile_name"] == "backend_mumbai"  # profile_id stored
        assert apps[0]["company_name"] == "Acme"

    def test_fill_result_stored_in_result(self, db, profile, mock_filler):
        result = self._run_with_answer("y", db, profile, mock_filler)
        assert "first_name" in result.fields_filled
        assert "phone" in result.fields_skipped


class TestApplyResult:
    def test_submitted_result(self):
        r = ApplyResult(
            status="SUBMITTED",
            fields_filled=["name"],
            fields_skipped=[],
            failure_reason="",
        )
        assert r.status == "SUBMITTED"
        assert r.failure_reason == ""

    def test_failed_result(self):
        r = ApplyResult(
            status="FAILED",
            fields_filled=[],
            fields_skipped=[],
            failure_reason="HUMAN_REJECTED",
        )
        assert r.failure_reason == "HUMAN_REJECTED"
