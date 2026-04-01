"""Tests for base scraper contract."""
import pytest
from datetime import datetime, timezone

from src.scrapers.base import BaseScraper, RawJob, ScraperResult


class DummyScraper(BaseScraper):
    """Concrete test implementation of BaseScraper."""

    def __init__(self, url, jobs_to_return=None, should_raise=False):
        super().__init__(url)
        self._jobs = jobs_to_return or []
        self._should_raise = should_raise

    def source_name(self) -> str:
        return "dummy"

    def fetch_jobs(self) -> list[RawJob]:
        if self._should_raise:
            raise ConnectionError("Simulated network failure")
        return self._jobs


class TestRawJob:
    def test_create_raw_job(self):
        raw = RawJob(
            company_name="TestCorp",
            job_title="Engineer",
            job_description="Work here.",
            job_link="https://example.com/jobs/1",
        )
        assert raw.company_name == "TestCorp"
        assert raw.posted_timestamp is None


class TestBaseScraper:
    def test_scrape_returns_result(self):
        raw_jobs = [
            RawJob("TestCorp", "Engineer", "Desc", "https://example.com/jobs/1"),
        ]
        scraper = DummyScraper("https://example.com/careers", jobs_to_return=raw_jobs)
        result = scraper.scrape()
        assert isinstance(result, ScraperResult)
        assert result.source_name == "dummy"
        assert len(result.jobs) == 1
        assert result.errors == []

    def test_scrape_captures_errors(self):
        scraper = DummyScraper("https://example.com/careers", should_raise=True)
        result = scraper.scrape()
        assert result.jobs == []
        assert len(result.errors) == 1
        assert "Simulated network failure" in result.errors[0]

    def test_scrape_records_timing(self):
        scraper = DummyScraper("https://example.com/careers")
        result = scraper.scrape()
        assert result.started_at is not None
        assert result.ended_at is not None
        assert result.ended_at >= result.started_at

    def test_source_url_stored(self):
        scraper = DummyScraper("https://example.com/careers")
        assert scraper.url == "https://example.com/careers"
