"""Tests for Nasdaq scraper adapter (Workday CXS REST API)."""
from unittest.mock import patch, MagicMock

from src.scrapers.nasdaq import NasdaqScraper, _parse_jobs_from_response
from src.scrapers.base import RawJob


SAMPLE_RESPONSE = {
    "total": 2,
    "jobPostings": [
        {
            "title": "Software Engineer",
            "externalPath": "/job/R0012345",
            "locationsText": "Mumbai, India",
            "bulletFields": ["R0012345"],
        },
        {
            "title": "Senior Developer",
            "externalPath": "/job/R0012346",
            "locationsText": "Pune, India",
            "bulletFields": ["R0012346"],
        },
    ],
}

EMPTY_RESPONSE = {"total": 0, "jobPostings": []}


class TestParseJobsFromResponse:
    def test_parses_jobs(self):
        jobs, total = _parse_jobs_from_response(SAMPLE_RESPONSE)
        assert len(jobs) == 2
        assert total == 2
        assert jobs[0].company_name == "Nasdaq"
        assert jobs[0].job_title == "Software Engineer"
        assert jobs[0].location == "Mumbai, India"
        assert "R0012345" in jobs[0].job_link

    def test_empty_response(self):
        jobs, total = _parse_jobs_from_response(EMPTY_RESPONSE)
        assert len(jobs) == 0
        assert total == 0

    def test_missing_bullet_fields(self):
        data = {"total": 1, "jobPostings": [
            {"title": "Analyst", "externalPath": "/job/X1", "locationsText": "", "bulletFields": []}
        ]}
        jobs, total = _parse_jobs_from_response(data)
        assert len(jobs) == 1
        assert jobs[0].job_description == "Analyst"

    def test_description_includes_location_and_req_id(self):
        jobs, _ = _parse_jobs_from_response(SAMPLE_RESPONSE)
        assert "Mumbai, India" in jobs[0].job_description
        assert "R0012345" in jobs[0].job_description


class TestNasdaqScraper:
    def test_source_name(self):
        scraper = NasdaqScraper("https://nasdaq.wd1.myworkdayjobs.com/...")
        assert scraper.source_name() == "nasdaq"

    @patch("src.scrapers.nasdaq.httpx")
    def test_fetch_jobs_single_page(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_resp

        scraper = NasdaqScraper("https://nasdaq.wd1.myworkdayjobs.com/...")
        jobs = scraper.fetch_jobs()
        assert len(jobs) == 2

    @patch("src.scrapers.nasdaq.httpx")
    def test_fetch_jobs_pagination(self, mock_httpx):
        page1 = {"total": 25, "jobPostings": [
            {"title": f"Job {i}", "externalPath": f"/job/{i}", "locationsText": "Mumbai", "bulletFields": []}
            for i in range(20)
        ]}
        page2 = {"total": 25, "jobPostings": [
            {"title": f"Job {i}", "externalPath": f"/job/{i}", "locationsText": "Mumbai", "bulletFields": []}
            for i in range(20, 25)
        ]}

        mock_resp1 = MagicMock()
        mock_resp1.json.return_value = page1
        mock_resp1.raise_for_status = MagicMock()
        mock_resp2 = MagicMock()
        mock_resp2.json.return_value = page2
        mock_resp2.raise_for_status = MagicMock()
        mock_httpx.post.side_effect = [mock_resp1, mock_resp2]

        scraper = NasdaqScraper("https://nasdaq.wd1.myworkdayjobs.com/...")
        jobs = scraper.fetch_jobs()
        assert len(jobs) == 25
