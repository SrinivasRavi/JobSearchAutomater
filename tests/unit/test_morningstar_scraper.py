"""Tests for Morningstar scraper adapter (Phenom People JS data)."""
import pytest
from unittest.mock import patch, MagicMock

from src.scrapers.morningstar import MorningstarScraper, _extract_jobs_from_html, _parse_jobs
from src.scrapers.base import RawJob

SAMPLE_HTML = """
<html><body>
<script>
phApp.ddo = {"eagerLoadRefineSearch":{"status":200,"hits":2,"totalHits":2,"data":{"jobs":[
{"jobId":"12345","title":"Software Engineer","location":"Mumbai, India","city":"Mumbai","country":"India","descriptionTeaser":"Build analytics tools.","applyUrl":"https://careers.morningstar.com/us/en/job/12345","category":"Product Development","type":"Full time","postedDate":"2026-03-15T00:00:00"},
{"jobId":"12346","title":"Senior Developer","location":"Pune, India","city":"Pune","country":"India","descriptionTeaser":"Lead development.","applyUrl":"https://careers.morningstar.com/us/en/job/12346","category":"Product Development","type":"Full time","postedDate":"2026-03-20T00:00:00"}
]}}};
</script>
</body></html>
"""

EMPTY_HTML = """
<html><body>
<script>
phApp.ddo = {"eagerLoadRefineSearch":{"status":200,"hits":0,"totalHits":0,"data":{"jobs":[]}}};
</script>
</body></html>
"""

NO_DATA_HTML = "<html><body><p>No data</p></body></html>"


class TestExtractJobsFromHtml:
    def test_extracts_jobs(self):
        jobs, total = _extract_jobs_from_html(SAMPLE_HTML)
        assert len(jobs) == 2
        assert total == 2
        assert jobs[0]["title"] == "Software Engineer"
        assert jobs[0]["jobId"] == "12345"

    def test_empty_jobs(self):
        jobs, total = _extract_jobs_from_html(EMPTY_HTML)
        assert len(jobs) == 0
        assert total == 0

    def test_no_phapp_data(self):
        jobs, total = _extract_jobs_from_html(NO_DATA_HTML)
        assert len(jobs) == 0
        assert total == 0


class TestParseJobs:
    def test_parses_raw_jobs(self):
        raw = [
            {"jobId": "12345", "title": "Software Engineer", "location": "Mumbai, India",
             "descriptionTeaser": "Build things.", "applyUrl": "https://careers.morningstar.com/us/en/job/12345"},
        ]
        jobs = _parse_jobs(raw)
        assert len(jobs) == 1
        assert jobs[0].company_name == "Morningstar"
        assert jobs[0].job_title == "Software Engineer"
        assert jobs[0].location == "Mumbai, India"
        assert "morningstar.com" in jobs[0].job_link

    def test_fallback_url_when_no_apply_url(self):
        raw = [{"jobId": "99999", "title": "Analyst", "location": "", "descriptionTeaser": ""}]
        jobs = _parse_jobs(raw)
        assert "99999" in jobs[0].job_link


class TestMorningstarScraper:
    def test_source_name(self):
        scraper = MorningstarScraper("https://careers.morningstar.com/us/en/c/product-development-jobs")
        assert scraper.source_name() == "morningstar"

    @patch("src.scrapers.morningstar.httpx")
    def test_fetch_jobs(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_HTML
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_resp

        scraper = MorningstarScraper("https://careers.morningstar.com/us/en/c/product-development-jobs")
        jobs = scraper.fetch_jobs()
        assert len(jobs) == 2
        assert jobs[0].location == "Mumbai, India"

    @patch("src.scrapers.morningstar.httpx")
    def test_handles_error(self, mock_httpx):
        mock_httpx.get.side_effect = ConnectionError("timeout")
        scraper = MorningstarScraper("https://careers.morningstar.com/us/en/c/product-development-jobs")
        result = scraper.scrape()
        assert result.jobs == []
        assert len(result.errors) == 1
