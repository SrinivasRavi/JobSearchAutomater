"""Tests for Deutsche Bank scraper adapter."""
import pytest
from unittest.mock import patch, MagicMock

from src.scrapers.deutsche_bank import DeutscheBankScraper, _parse_jobs_from_response
from src.scrapers.base import RawJob

SAMPLE_API_RESPONSE = {
    "SearchResult": {
        "SearchResultCount": 2,
        "SearchResultCountAll": 2,
        "SearchResultItems": [
            {
                "MatchedObjectDescriptor": {
                    "PositionID": "R0012345",
                    "PositionTitle": "Software Engineer",
                    "PositionURI": "/index.php?ac=jobad&id=12345",
                    "PositionLocation": [{"CityName": "Mumbai", "CountryName": "India"}],
                    "OrganizationName": "Technology",
                    "PublicationStartDate": "2026-03-15",
                },
            },
            {
                "MatchedObjectDescriptor": {
                    "PositionID": "R0012346",
                    "PositionTitle": "Senior Java Developer",
                    "PositionURI": "/index.php?ac=jobad&id=12346",
                    "PositionLocation": [{"CityName": "Mumbai", "CountryName": "India"}],
                    "OrganizationName": "Technology",
                    "PublicationStartDate": "2026-03-20",
                },
            },
        ],
    }
}


class TestParseDeutscheBankResponse:
    def test_parses_jobs(self):
        jobs = _parse_jobs_from_response(SAMPLE_API_RESPONSE)
        assert len(jobs) == 2
        assert jobs[0].company_name == "Deutsche Bank"
        assert jobs[0].job_title == "Software Engineer"
        assert "careers.db.com" in jobs[0].job_link

    def test_empty_response(self):
        empty = {"SearchResult": {"SearchResultCount": 0, "SearchResultItems": []}}
        jobs = _parse_jobs_from_response(empty)
        assert len(jobs) == 0


class TestDeutscheBankScraper:
    def test_source_name(self):
        scraper = DeutscheBankScraper("https://careers.db.com/professionals/search-roles/")
        assert scraper.source_name() == "deutsche_bank"

    @patch("src.scrapers.deutsche_bank.httpx")
    def test_fetch_jobs(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = SAMPLE_API_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_resp

        scraper = DeutscheBankScraper("https://careers.db.com/professionals/search-roles/#/professional/results/?category=1328&profession=1330&country=81")
        jobs = scraper.fetch_jobs()
        assert len(jobs) == 2
