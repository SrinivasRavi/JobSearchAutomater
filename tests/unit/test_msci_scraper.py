"""Tests for MSCI scraper adapter (Algolia API)."""
import pytest
from unittest.mock import patch, MagicMock

from src.scrapers.msci import MsciScraper, _parse_jobs_from_response
from src.scrapers.base import RawJob

SAMPLE_API_RESPONSE = {
    "hits": [
        {
            "objectID": "12345",
            "title": "Software Developer",
            "town_city": "Mumbai",
            "country": "India",
            "brand": "MSCI",
            "description": "Build financial analytics tools.",
            "ats_requisition_id": "REQ-12345",
            "role_category": "Hybrid",
        },
        {
            "objectID": "12346",
            "title": "Senior Developer",
            "town_city": "Mumbai",
            "country": "India",
            "brand": "MSCI",
            "description": "Lead development team.",
            "ats_requisition_id": "REQ-12346",
            "role_category": "On-site",
        },
    ],
    "nbHits": 2,
    "page": 0,
    "nbPages": 1,
    "hitsPerPage": 20,
}


class TestParseMsciResponse:
    def test_parses_jobs(self):
        jobs = _parse_jobs_from_response(SAMPLE_API_RESPONSE)
        assert len(jobs) == 2
        assert jobs[0].company_name == "MSCI"
        assert jobs[0].job_title == "Software Developer"
        assert "careers.msci.com" in jobs[0].job_link
        assert jobs[0].location == "Mumbai, India"

    def test_empty_response(self):
        jobs = _parse_jobs_from_response({"hits": [], "nbHits": 0})
        assert len(jobs) == 0


class TestMsciScraper:
    def test_source_name(self):
        scraper = MsciScraper("https://careers.msci.com/job-search")
        assert scraper.source_name() == "msci"

    @patch("src.scrapers.msci.httpx")
    def test_fetch_jobs(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = SAMPLE_API_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_resp

        scraper = MsciScraper("https://careers.msci.com/job-search?production__mscicare2201__sort-rank%5Bquery%5D=Developer")
        jobs = scraper.fetch_jobs()
        assert len(jobs) == 2
