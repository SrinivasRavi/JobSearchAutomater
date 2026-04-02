"""Tests for ApplicationRepository — TDD for Task 2."""
import pytest

from src.persistence.database import Database
from src.persistence.repository import ApplicationRepository


@pytest.fixture
def db():
    d = Database(":memory:")
    d.initialize()
    yield d
    d.close()


@pytest.fixture
def repo(db):
    return ApplicationRepository(db.connection)


class TestCreateApplication:
    def test_returns_int_id(self, repo):
        app_id = repo.create_application(
            job_id=None, profile_name="backend", job_url="https://example.com/apply"
        )
        assert isinstance(app_id, int)
        assert app_id > 0

    def test_nullable_job_id(self, repo):
        app_id = repo.create_application(
            job_id=None, profile_name="backend", job_url="https://example.com/apply"
        )
        assert app_id > 0

    def test_default_status_is_pending(self, repo):
        repo.create_application(
            job_id=None, profile_name="backend", job_url="https://x.com"
        )
        apps = repo.list_applications()
        assert apps[0]["status"] == "PENDING"

    def test_stores_metadata(self, repo):
        repo.create_application(
            job_id=None,
            profile_name="backend",
            job_url="https://x.com",
            job_title="SWE",
            company_name="Acme",
            ats_platform="workday",
            apply_method="cli",
        )
        apps = repo.list_applications()
        a = apps[0]
        assert a["job_title"] == "SWE"
        assert a["company_name"] == "Acme"
        assert a["ats_platform"] == "workday"
        assert a["apply_method"] == "cli"
        assert a["profile_name"] == "backend"


class TestUpdateStatus:
    def test_updates_status(self, repo):
        app_id = repo.create_application(job_id=None, profile_name="p", job_url="u")
        repo.update_status(app_id, "SUBMITTED")
        apps = repo.list_applications()
        assert apps[0]["status"] == "SUBMITTED"

    def test_stores_failure_reason(self, repo):
        app_id = repo.create_application(job_id=None, profile_name="p", job_url="u")
        repo.update_status(app_id, "FAILED", failure_reason="LOGIN_REQUIRED")
        apps = repo.list_applications()
        assert apps[0]["failure_reason"] == "LOGIN_REQUIRED"

    def test_stores_notes(self, repo):
        app_id = repo.create_application(job_id=None, profile_name="p", job_url="u")
        repo.update_status(app_id, "SKIPPED", notes="Not relevant")
        apps = repo.list_applications()
        assert apps[0]["notes"] == "Not relevant"

    def test_sets_applied_timestamp_on_submitted(self, repo):
        app_id = repo.create_application(job_id=None, profile_name="p", job_url="u")
        repo.update_status(app_id, "SUBMITTED")
        apps = repo.list_applications()
        assert apps[0]["applied_timestamp"] is not None


class TestLogAttempt:
    def test_logs_attempt(self, repo):
        app_id = repo.create_application(job_id=None, profile_name="p", job_url="u")
        repo.log_attempt(app_id, result="SUCCESS")
        attempts = repo.get_attempts(app_id)
        assert len(attempts) == 1
        assert attempts[0]["result"] == "SUCCESS"

    def test_logs_error_message(self, repo):
        app_id = repo.create_application(job_id=None, profile_name="p", job_url="u")
        repo.log_attempt(app_id, result="FAILED", error_message="Timeout")
        attempts = repo.get_attempts(app_id)
        assert attempts[0]["error_message"] == "Timeout"

    def test_logs_screenshot_path(self, repo):
        app_id = repo.create_application(job_id=None, profile_name="p", job_url="u")
        repo.log_attempt(app_id, result="SUCCESS", screenshot_path="data/screenshots/1_after.png")
        attempts = repo.get_attempts(app_id)
        assert attempts[0]["screenshot_path"] == "data/screenshots/1_after.png"

    def test_multiple_attempts(self, repo):
        app_id = repo.create_application(job_id=None, profile_name="p", job_url="u")
        repo.log_attempt(app_id, result="FAILED")
        repo.log_attempt(app_id, result="SUCCESS")
        assert len(repo.get_attempts(app_id)) == 2


class TestGetByJobId:
    def test_returns_application(self, db, repo):
        # Insert a real job so FK is satisfied
        db.connection.execute(
            "INSERT INTO jobs (company_name, job_title, job_description, job_link, clean_job_link, "
            "scraped_timestamp, source_type, source_name) VALUES (?,?,?,?,?,?,?,?)",
            ("Acme", "SWE", "desc", "https://x.com", "https://x.com", "2024-01-01", "api", "acme"),
        )
        db.connection.commit()
        job_id = db.connection.execute("SELECT job_id FROM jobs").fetchone()[0]
        app_id = repo.create_application(job_id=job_id, profile_name="p", job_url="u")
        result = repo.get_by_job_id(job_id)
        assert result is not None
        assert result["id"] == app_id

    def test_returns_none_for_missing(self, repo):
        assert repo.get_by_job_id(999) is None


class TestGetPendingJobs:
    def test_returns_empty_when_no_jobs(self, db, repo):
        result = repo.get_pending_jobs()
        assert result == []

    def test_returns_not_applied_jobs_without_application(self, db, repo):
        # Insert a job directly
        db.connection.execute(
            "INSERT INTO jobs (company_name, job_title, job_description, job_link, clean_job_link, "
            "scraped_timestamp, source_type, source_name) VALUES (?,?,?,?,?,?,?,?)",
            ("Acme", "SWE", "desc", "https://x.com", "https://x.com", "2024-01-01", "api", "acme"),
        )
        db.connection.commit()
        result = repo.get_pending_jobs(limit=10)
        assert len(result) == 1
        assert result[0]["company_name"] == "Acme"

    def test_excludes_already_applied_jobs(self, db, repo):
        db.connection.execute(
            "INSERT INTO jobs (company_name, job_title, job_description, job_link, clean_job_link, "
            "scraped_timestamp, source_type, source_name) VALUES (?,?,?,?,?,?,?,?)",
            ("Acme", "SWE", "desc", "https://x.com", "https://x.com", "2024-01-01", "api", "acme"),
        )
        db.connection.commit()
        job_id = db.connection.execute("SELECT job_id FROM jobs").fetchone()[0]
        repo.create_application(job_id=job_id, profile_name="p", job_url="https://x.com")
        result = repo.get_pending_jobs()
        assert result == []


class TestGetStats:
    def test_empty_stats(self, repo):
        stats = repo.get_stats()
        assert "by_status" in stats
        assert "by_profile" in stats
        assert "by_method" in stats

    def test_counts_by_status(self, repo):
        repo.create_application(job_id=None, profile_name="p", job_url="u")
        repo.create_application(job_id=None, profile_name="p", job_url="u2")
        app_id = repo.create_application(job_id=None, profile_name="p", job_url="u3")
        repo.update_status(app_id, "SUBMITTED")
        stats = repo.get_stats()
        assert stats["by_status"].get("PENDING", 0) == 2
        assert stats["by_status"].get("SUBMITTED", 0) == 1

    def test_counts_by_profile(self, repo):
        repo.create_application(job_id=None, profile_name="backend", job_url="u1")
        repo.create_application(job_id=None, profile_name="fullstack", job_url="u2")
        repo.create_application(job_id=None, profile_name="backend", job_url="u3")
        stats = repo.get_stats()
        assert stats["by_profile"]["backend"] == 2
        assert stats["by_profile"]["fullstack"] == 1

    def test_counts_by_method(self, repo):
        repo.create_application(job_id=None, profile_name="p", job_url="u1", apply_method="cli")
        repo.create_application(job_id=None, profile_name="p", job_url="u2", apply_method="extension")
        stats = repo.get_stats()
        assert stats["by_method"]["cli"] == 1
        assert stats["by_method"]["extension"] == 1


class TestListApplications:
    def test_filter_by_status(self, repo):
        repo.create_application(job_id=None, profile_name="p", job_url="u1")
        app_id = repo.create_application(job_id=None, profile_name="p", job_url="u2")
        repo.update_status(app_id, "SUBMITTED")
        submitted = repo.list_applications(status="SUBMITTED")
        assert len(submitted) == 1

    def test_filter_by_profile(self, repo):
        repo.create_application(job_id=None, profile_name="backend", job_url="u1")
        repo.create_application(job_id=None, profile_name="fullstack", job_url="u2")
        result = repo.list_applications(profile="backend")
        assert len(result) == 1
        assert result[0]["profile_name"] == "backend"

    def test_respects_limit(self, repo):
        for i in range(5):
            repo.create_application(job_id=None, profile_name="p", job_url=f"u{i}")
        result = repo.list_applications(limit=3)
        assert len(result) == 3
