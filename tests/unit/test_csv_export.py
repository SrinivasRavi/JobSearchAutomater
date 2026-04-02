"""Tests for CSV export."""
import csv
import io
import os
import pytest
import tempfile
from datetime import datetime, timezone

from src.models.job import Job
from src.models.enums import ApplicationStatus, SourceType
from src.persistence.database import Database
from src.persistence.repository import JobRepository
from src.utils.csv_export import export_jobs_csv


@pytest.fixture
def repo():
    db = Database(":memory:")
    db.initialize()
    return JobRepository(db)


def _insert_job(repo, company="TestCorp", title="Engineer", link_suffix="1"):
    job = Job(
        company_name=company,
        job_title=title,
        job_description="Desc",
        job_link=f"https://example.com/jobs/{link_suffix}?ref=x",
        clean_job_link=f"https://example.com/jobs/{link_suffix}",
        scraped_timestamp=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
        application_status=ApplicationStatus.NOT_APPLIED,
        source_type=SourceType.CAREER_PAGE,
        source_name="test",
        posted_timestamp=datetime(2026, 3, 30, tzinfo=timezone.utc),
    )
    repo.insert(job)


class TestCsvExport:
    def test_export_to_string(self, repo):
        _insert_job(repo)
        output = io.StringIO()
        export_jobs_csv(repo, output)
        output.seek(0)
        reader = csv.DictReader(output)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["company_name"] == "TestCorp"
        assert rows[0]["job_title"] == "Engineer"

    def test_export_has_all_columns(self, repo):
        _insert_job(repo)
        output = io.StringIO()
        export_jobs_csv(repo, output)
        output.seek(0)
        reader = csv.DictReader(output)
        row = next(reader)
        expected_cols = {
            "job_id", "company_name", "job_title", "location", "job_link",
            "clean_job_link", "posted_timestamp", "scraped_timestamp",
            "application_status", "source_type", "source_name",
        }
        assert expected_cols.issubset(set(row.keys()))

    def test_export_multiple_jobs(self, repo):
        _insert_job(repo, company="AlphaCorp", link_suffix="1")
        _insert_job(repo, company="BetaCorp", link_suffix="2")
        output = io.StringIO()
        export_jobs_csv(repo, output)
        output.seek(0)
        rows = list(csv.DictReader(output))
        assert len(rows) == 2

    def test_export_to_file(self, repo):
        _insert_job(repo)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            path = f.name
            export_jobs_csv(repo, f)
        try:
            with open(path) as f:
                rows = list(csv.DictReader(f))
            assert len(rows) == 1
        finally:
            os.unlink(path)

    def test_export_empty_db(self, repo):
        output = io.StringIO()
        export_jobs_csv(repo, output)
        output.seek(0)
        rows = list(csv.DictReader(output))
        assert len(rows) == 0
