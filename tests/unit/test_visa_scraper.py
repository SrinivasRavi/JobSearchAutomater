"""Tests for Visa scraper adapter."""
import pytest
from unittest.mock import patch, MagicMock

from src.scrapers.visa import VisaScraper, _parse_jobs_from_response
from src.scrapers.base import RawJob

SAMPLE_API_RESPONSE = {
    "totalFound": 2,
    "offset": 0,
    "limit": 100,
    "content": [
        {
            "id": "743999123456",
            "uuid": "abc-123",
            "name": "Software Engineer",
            "refNumber": "REF123",
            "releasedDate": "2026-03-15T00:00:00.000Z",
            "company": {"name": "Visa"},
            "location": {"city": "Mumbai", "region": "Maharashtra", "country": "India"},
            "department": {"label": "Software Development/Engineering"},
            "ref": "https://jobs.smartrecruiters.com/Visa/743999123456-software-engineer",
        },
        {
            "id": "743999123457",
            "uuid": "def-456",
            "name": "Senior Backend Engineer",
            "refNumber": "REF456",
            "releasedDate": "2026-03-20T00:00:00.000Z",
            "company": {"name": "Visa"},
            "location": {"city": "Mumbai", "region": "Maharashtra", "country": "India"},
            "department": {"label": "Software Development/Engineering"},
            "ref": "https://jobs.smartrecruiters.com/Visa/743999123457-senior-backend-engineer",
        },
    ],
}


class TestParseVisaResponse:
    def test_parses_jobs(self):
        jobs = _parse_jobs_from_response(SAMPLE_API_RESPONSE)
        assert len(jobs) == 2
        assert jobs[0].company_name == "Visa"
        assert jobs[0].job_title == "Software Engineer"
        assert "smartrecruiters.com/Visa/" in jobs[0].job_link

    def test_empty_response(self):
        jobs = _parse_jobs_from_response({"totalFound": 0, "content": []})
        assert len(jobs) == 0


class TestVisaScraper:
    def test_source_name(self):
        scraper = VisaScraper("https://www.visa.co.uk/en_gb/jobs/?cities=Mumbai")
        assert scraper.source_name() == "visa"

    @patch("src.scrapers.visa.httpx")
    def test_fetch_jobs(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = SAMPLE_API_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_resp

        scraper = VisaScraper("https://www.visa.co.uk/en_gb/jobs/?categories=Software%20Development%2FEngineering&cities=Mumbai")
        jobs = scraper.fetch_jobs()
        assert len(jobs) == 2
