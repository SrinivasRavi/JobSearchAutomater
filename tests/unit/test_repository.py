"""Tests for job persistence and dedupe."""
import pytest
import sqlite3
from datetime import datetime, timezone

from src.models.job import Job
from src.models.enums import ApplicationStatus, SourceType
from src.persistence.database import Database
from src.persistence.repository import JobRepository


@pytest.fixture
def db():
    """Create an in-memory database for testing."""
    database = Database(":memory:")
    database.initialize()
    return database


@pytest.fixture
def repo(db):
    return JobRepository(db)


def _make_job(**overrides):
    defaults = {
        "company_name": "TestCorp",
        "job_title": "Software Engineer",
        "job_description": "Build things.",
        "job_link": "https://example.com/jobs/123?ref=search",
        "clean_job_link": "https://example.com/jobs/123",
        "scraped_timestamp": datetime.now(timezone.utc),
        "application_status": ApplicationStatus.NOT_APPLIED,
        "source_type": SourceType.CAREER_PAGE,
        "source_name": "testcorp",
    }
    defaults.update(overrides)
    return Job(**defaults)


class TestJobRepository:
    def test_insert_job(self, repo):
        job = _make_job()
        job_id = repo.insert(job)
        assert job_id is not None
        assert isinstance(job_id, int)

    def test_insert_returns_id(self, repo):
        job = _make_job()
        job_id = repo.insert(job)
        assert job_id >= 1

    def test_get_by_id(self, repo):
        job = _make_job()
        job_id = repo.insert(job)
        retrieved = repo.get_by_id(job_id)
        assert retrieved is not None
        assert retrieved.company_name == "TestCorp"
        assert retrieved.job_id == job_id

    def test_duplicate_clean_link_rejected(self, repo):
        job1 = _make_job()
        job2 = _make_job(job_link="https://example.com/jobs/123?ref=other")
        repo.insert(job1)
        result = repo.insert(job2)
        assert result is None

    def test_different_clean_links_both_inserted(self, repo):
        job1 = _make_job(clean_job_link="https://example.com/jobs/123")
        job2 = _make_job(clean_job_link="https://example.com/jobs/456",
                         job_link="https://example.com/jobs/456?ref=x")
        id1 = repo.insert(job1)
        id2 = repo.insert(job2)
        assert id1 is not None
        assert id2 is not None
        assert id1 != id2

    def test_exists_by_clean_link(self, repo):
        job = _make_job()
        assert repo.exists("https://example.com/jobs/123") is False
        repo.insert(job)
        assert repo.exists("https://example.com/jobs/123") is True

    def test_count_all(self, repo):
        assert repo.count() == 0
        repo.insert(_make_job(clean_job_link="https://example.com/jobs/1"))
        repo.insert(_make_job(clean_job_link="https://example.com/jobs/2"))
        assert repo.count() == 2

    def test_count_by_status(self, repo):
        repo.insert(_make_job(clean_job_link="https://example.com/jobs/1"))
        repo.insert(_make_job(clean_job_link="https://example.com/jobs/2",
                              application_status=ApplicationStatus.APPLIED))
        assert repo.count(status=ApplicationStatus.NOT_APPLIED) == 1
        assert repo.count(status=ApplicationStatus.APPLIED) == 1

    def test_list_jobs(self, repo):
        repo.insert(_make_job(clean_job_link="https://example.com/jobs/1"))
        repo.insert(_make_job(clean_job_link="https://example.com/jobs/2"))
        jobs = repo.list_jobs()
        assert len(jobs) == 2

    def test_list_jobs_with_limit(self, repo):
        for i in range(5):
            repo.insert(_make_job(clean_job_link=f"https://example.com/jobs/{i}"))
        jobs = repo.list_jobs(limit=3)
        assert len(jobs) == 3

    def test_list_jobs_by_company(self, repo):
        repo.insert(_make_job(clean_job_link="https://example.com/jobs/1",
                              company_name="AlphaCorp"))
        repo.insert(_make_job(clean_job_link="https://example.com/jobs/2",
                              company_name="BetaCorp"))
        jobs = repo.list_jobs(company_name="AlphaCorp")
        assert len(jobs) == 1
        assert jobs[0].company_name == "AlphaCorp"

    def test_update_status(self, repo):
        job_id = repo.insert(_make_job())
        repo.update_status(job_id, ApplicationStatus.APPLIED)
        job = repo.get_by_id(job_id)
        assert job.application_status == ApplicationStatus.APPLIED


class TestScrapeRunLog:
    def test_insert_run_log(self, repo):
        run_id = repo.log_scrape_run(
            source_name="testcorp",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            jobs_discovered=10,
            jobs_inserted=8,
            jobs_skipped=2,
            errors_count=0,
        )
        assert run_id is not None

    def test_insert_error_log(self, repo):
        run_id = repo.log_scrape_run(
            source_name="testcorp",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            jobs_discovered=0,
            jobs_inserted=0,
            jobs_skipped=0,
            errors_count=1,
        )
        repo.log_scrape_error(
            run_id=run_id,
            source_name="testcorp",
            error_type="PARSE_ERROR",
            message="Could not find job title element",
        )
        # Should not raise


class TestDatabaseSchema:
    def test_tables_exist(self, db):
        conn = db.connection
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}
        assert "jobs" in tables
        assert "scrape_runs" in tables
        assert "scrape_errors" in tables

    def test_jobs_unique_constraint_on_clean_link(self, db):
        conn = db.connection
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO jobs (company_name, job_title, job_description, job_link, "
            "clean_job_link, scraped_timestamp, application_status, source_type, source_name) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("A", "B", "C", "http://x.com/1?r=1", "http://x.com/1", now, "NOT_APPLIED", "CAREER_PAGE", "test"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO jobs (company_name, job_title, job_description, job_link, "
                "clean_job_link, scraped_timestamp, application_status, source_type, source_name) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("A", "B", "C", "http://x.com/1?r=2", "http://x.com/1", now, "NOT_APPLIED", "CAREER_PAGE", "test"),
            )
