"""Tests for Amazon Jobs scraper adapter."""
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.scrapers.amazon import AmazonScraper, _parse_jobs_from_response
from src.scrapers.base import RawJob


SAMPLE_API_RESPONSE = {
    "jobs": [
        {
            "id_icims": "2920188",
            "title": "Software Development Engineer",
            "company_name": "Amazon",
            "description_short": "Design and build systems at scale.",
            "location": "Mumbai, Maharashtra, IND",
            "posted_date": "March 28, 2026",
            "job_path": "/en/jobs/2920188/software-development-engineer",
            "url_next_step": "https://www.amazon.jobs/en/jobs/2920188/software-development-engineer",
        },
        {
            "id_icims": "2918500",
            "title": "Sr. Software Development Engineer",
            "company_name": "Amazon",
            "description_short": "Lead backend development.",
            "location": "Mumbai, Maharashtra, IND",
            "posted_date": "March 25, 2026",
            "job_path": "/en/jobs/2918500/sr-software-development-engineer",
            "url_next_step": "https://www.amazon.jobs/en/jobs/2918500/sr-software-development-engineer",
        },
    ],
    "hits": 2,
}

EMPTY_API_RESPONSE = {
    "jobs": [],
    "hits": 0,
}


class TestParseJobsFromResponse:
    def test_parses_jobs(self):
        jobs = _parse_jobs_from_response(SAMPLE_API_RESPONSE)
        assert len(jobs) == 2
        assert jobs[0].company_name == "Amazon"
        assert jobs[0].job_title == "Software Development Engineer"
        assert "Design and build" in jobs[0].job_description
        assert "amazon.jobs" in jobs[0].job_link
        assert jobs[0].location == "Mumbai, Maharashtra, IND"

    def test_empty_response(self):
        jobs = _parse_jobs_from_response(EMPTY_API_RESPONSE)
        assert len(jobs) == 0

    def test_job_link_is_full_url(self):
        jobs = _parse_jobs_from_response(SAMPLE_API_RESPONSE)
        assert jobs[0].job_link.startswith("https://")


class TestAmazonScraper:
    def test_source_name(self):
        scraper = AmazonScraper("https://www.amazon.jobs/en/search?base_query=software")
        assert scraper.source_name() == "amazon"

    @patch("src.scrapers.amazon.httpx")
    def test_fetch_jobs_calls_json_api(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_API_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        scraper = AmazonScraper("https://www.amazon.jobs/en/search?offset=0&result_limit=10&sort=relevant&base_query=software&city=Mumbai&country=IND")
        jobs = scraper.fetch_jobs()
        assert len(jobs) == 2

        called_url = mock_httpx.get.call_args[0][0]
        assert "search.json" in called_url

    @patch("src.scrapers.amazon.httpx")
    def test_fetch_jobs_paginates(self, mock_httpx):
        """Should fetch multiple pages if hits > result_limit."""
        page1 = {"jobs": [SAMPLE_API_RESPONSE["jobs"][0]], "hits": 2}
        page2 = {"jobs": [SAMPLE_API_RESPONSE["jobs"][1]], "hits": 2}

        mock_resp1 = MagicMock()
        mock_resp1.status_code = 200
        mock_resp1.json.return_value = page1
        mock_resp1.raise_for_status = MagicMock()

        mock_resp2 = MagicMock()
        mock_resp2.status_code = 200
        mock_resp2.json.return_value = page2
        mock_resp2.raise_for_status = MagicMock()

        mock_httpx.get.side_effect = [mock_resp1, mock_resp2]

        scraper = AmazonScraper("https://www.amazon.jobs/en/search?offset=0&result_limit=1&base_query=software&city=Mumbai")
        jobs = scraper.fetch_jobs()
        assert len(jobs) == 2
        assert mock_httpx.get.call_count == 2

    @patch("src.scrapers.amazon.httpx")
    def test_fetch_jobs_handles_error(self, mock_httpx):
        mock_httpx.get.side_effect = ConnectionError("timeout")
        scraper = AmazonScraper("https://www.amazon.jobs/en/search?base_query=software")
        result = scraper.scrape()
        assert result.jobs == []
        assert len(result.errors) == 1
