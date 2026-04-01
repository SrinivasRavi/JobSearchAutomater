"""Tests for the scrape orchestrator."""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.models.enums import ApplicationStatus, SourceType
from src.models.job import Job
from src.persistence.database import Database
from src.persistence.repository import JobRepository
from src.scrapers.base import BaseScraper, RawJob, ScraperResult
from src.scrapers.orchestrator import ScrapeOrchestrator


class FakeScraper(BaseScraper):
    def __init__(self, url, jobs=None, should_raise=False):
        super().__init__(url)
        self._jobs = jobs or []
        self._should_raise = should_raise

    def source_name(self) -> str:
        return "fake"

    def fetch_jobs(self) -> list[RawJob]:
        if self._should_raise:
            raise ConnectionError("boom")
        return self._jobs


@pytest.fixture
def db():
    database = Database(":memory:")
    database.initialize()
    return database


@pytest.fixture
def repo(db):
    return JobRepository(db)


def _raw(title="Engineer", link="https://example.com/jobs/1"):
    return RawJob("TestCorp", title, "Desc", link)


class TestScrapeOrchestrator:
    def test_run_single_scraper_inserts_jobs(self, repo):
        scraper = FakeScraper("http://x.com", jobs=[_raw()])
        orch = ScrapeOrchestrator(repo)
        summary = orch.run([scraper])
        assert summary.total_discovered == 1
        assert summary.total_inserted == 1
        assert summary.total_skipped == 0
        assert repo.count() == 1

    def test_run_deduplicates_within_single_run(self, repo):
        scraper = FakeScraper("http://x.com", jobs=[
            _raw(link="https://example.com/jobs/1"),
            _raw(link="https://example.com/jobs/1?ref=dup"),
        ])
        orch = ScrapeOrchestrator(repo)
        summary = orch.run([scraper])
        assert summary.total_inserted == 1
        assert summary.total_skipped == 1

    def test_run_deduplicates_across_runs(self, repo):
        scraper1 = FakeScraper("http://x.com", jobs=[_raw()])
        scraper2 = FakeScraper("http://x.com", jobs=[_raw()])
        orch = ScrapeOrchestrator(repo)
        orch.run([scraper1])
        summary = orch.run([scraper2])
        assert summary.total_inserted == 0
        assert summary.total_skipped == 1
        assert repo.count() == 1

    def test_run_multiple_scrapers(self, repo):
        s1 = FakeScraper("http://a.com", jobs=[_raw(link="https://a.com/1")])
        s2 = FakeScraper("http://b.com", jobs=[_raw(link="https://b.com/2")])
        orch = ScrapeOrchestrator(repo)
        summary = orch.run([s1, s2])
        assert summary.total_discovered == 2
        assert summary.total_inserted == 2

    def test_run_continues_after_scraper_failure(self, repo):
        s1 = FakeScraper("http://a.com", should_raise=True)
        s2 = FakeScraper("http://b.com", jobs=[_raw(link="https://b.com/1")])
        orch = ScrapeOrchestrator(repo)
        summary = orch.run([s1, s2])
        assert summary.total_inserted == 1
        assert summary.total_errors > 0

    def test_run_logs_scrape_runs(self, repo):
        scraper = FakeScraper("http://x.com", jobs=[_raw()])
        orch = ScrapeOrchestrator(repo)
        orch.run([scraper])
        cursor = repo._db.connection.execute("SELECT COUNT(*) FROM scrape_runs")
        assert cursor.fetchone()[0] == 1

    def test_summary_has_per_source_details(self, repo):
        s1 = FakeScraper("http://a.com", jobs=[_raw(link="https://a.com/1")])
        orch = ScrapeOrchestrator(repo)
        summary = orch.run([s1])
        assert len(summary.source_results) == 1
        assert summary.source_results[0]["source"] == "fake"

    def test_empty_scraper_list(self, repo):
        orch = ScrapeOrchestrator(repo)
        summary = orch.run([])
        assert summary.total_discovered == 0
        assert summary.total_inserted == 0
