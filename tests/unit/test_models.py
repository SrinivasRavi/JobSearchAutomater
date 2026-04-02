"""Tests for Job model and status enums."""
import pytest
from datetime import datetime, timezone

from src.models.job import Job
from src.models.enums import ApplicationStatus, SourceType


class TestApplicationStatus:
    def test_default_status_is_not_applied(self):
        assert ApplicationStatus.NOT_APPLIED.value == "NOT_APPLIED"

    def test_all_v1_statuses_exist(self):
        expected = {"NOT_APPLIED", "APPLIED", "APPLY_FAILED", "HEARD_BACK", "REJECTED"}
        actual = {s.value for s in ApplicationStatus}
        assert expected.issubset(actual)

    def test_status_from_string(self):
        assert ApplicationStatus("NOT_APPLIED") == ApplicationStatus.NOT_APPLIED


class TestSourceType:
    def test_career_page_exists(self):
        assert SourceType.CAREER_PAGE.value == "CAREER_PAGE"

    def test_api_source_exists(self):
        assert SourceType.API.value == "API"

    def test_external_scraper_exists(self):
        assert SourceType.EXTERNAL_SCRAPER.value == "EXTERNAL_SCRAPER"


class TestJob:
    def _make_job(self, **overrides):
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

    def test_create_job_with_required_fields(self):
        job = self._make_job()
        assert job.company_name == "TestCorp"
        assert job.job_title == "Software Engineer"
        assert job.application_status == ApplicationStatus.NOT_APPLIED

    def test_posted_timestamp_defaults_to_none(self):
        job = self._make_job()
        assert job.posted_timestamp is None

    def test_job_id_defaults_to_none(self):
        job = self._make_job()
        assert job.job_id is None

    def test_job_with_posted_timestamp(self):
        ts = datetime(2026, 3, 15, tzinfo=timezone.utc)
        job = self._make_job(posted_timestamp=ts)
        assert job.posted_timestamp == ts

    def test_job_to_dict(self):
        job = self._make_job()
        d = job.to_dict()
        assert d["company_name"] == "TestCorp"
        assert d["application_status"] == "NOT_APPLIED"
        assert d["source_type"] == "CAREER_PAGE"
        assert "scraped_timestamp" in d

    def test_location_defaults_to_empty(self):
        job = self._make_job()
        assert job.location == ""

    def test_location_stored(self):
        job = self._make_job(location="Mumbai, India")
        assert job.location == "Mumbai, India"

    def test_job_clean_link_is_dedupe_key(self):
        job = self._make_job()
        assert job.dedupe_key == job.clean_job_link
