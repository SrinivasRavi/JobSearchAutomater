"""Integration test for the full scrape pipeline with real Amazon API."""
import csv
import io
import os
import tempfile
import pytest

from src.persistence.database import Database
from src.persistence.repository import JobRepository
from src.scrapers.amazon import AmazonScraper
from src.scrapers.orchestrator import ScrapeOrchestrator
from src.utils.csv_export import export_jobs_csv

AMAZON_URL = (
    "https://www.amazon.jobs/en/search?"
    "offset=0&result_limit=10&sort=relevant"
    "&category%5B%5D=software-development"
    "&job_type%5B%5D=Full-Time"
    "&distanceType=Mi&radius=24km"
    "&latitude=18.94018&longitude=72.83484"
    "&loc_query=Mumbai%2C%20Maharashtra%2C%20India"
    "&base_query=software&city=Mumbai&country=IND"
    "&region=Maharashtra&county=Mumbai"
)


@pytest.mark.integration
class TestFullPipeline:
    def test_scrape_persist_dedupe_export(self):
        db = Database(":memory:")
        db.initialize()
        repo = JobRepository(db)

        scraper = AmazonScraper(AMAZON_URL)
        orch = ScrapeOrchestrator(repo)

        # First run
        s1 = orch.run([scraper])
        assert s1.total_errors == 0
        assert s1.total_discovered > 0
        assert s1.total_inserted == s1.total_discovered

        # Second run — all should be skipped (dedupe)
        s2 = orch.run([scraper])
        assert s2.total_inserted == 0
        assert s2.total_skipped == s2.total_discovered

        # DB count matches
        assert repo.count() == s1.total_inserted

        # CSV export
        output = io.StringIO()
        count = export_jobs_csv(repo, output)
        assert count == s1.total_inserted

        output.seek(0)
        reader = csv.DictReader(output)
        rows = list(reader)
        assert len(rows) == s1.total_inserted
        for row in rows:
            assert row["company_name"]
            assert row["job_title"]
            assert row["job_link"].startswith("https://")
            assert row["application_status"] == "NOT_APPLIED"

        db.close()
