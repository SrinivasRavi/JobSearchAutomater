"""Tests for Oracle scraper adapter (Oracle HCM REST API)."""
from unittest.mock import patch, MagicMock

from src.scrapers.oracle_careers import OracleScraper, _parse_jobs_from_response
from src.scrapers.base import RawJob


SAMPLE_RESPONSE = {
    "items": [{
        "TotalJobsCount": 2,
        "requisitionList": [
            {
                "Id": "230100001",
                "Title": "Software Developer",
                "PrimaryLocation": "Mumbai, MH, IN",
                "ShortDescriptionStr": "Develop cloud infrastructure tools.",
            },
            {
                "Id": "230100002",
                "Title": "Cloud Engineer",
                "PrimaryLocation": "Bangalore, KA, IN",
                "ShortDescriptionStr": "Design distributed systems.",
            },
        ],
    }],
}

EMPTY_RESPONSE = {"items": [{"TotalJobsCount": 0, "requisitionList": []}]}


class TestParseJobsFromResponse:
    def test_parses_jobs(self):
        jobs, total = _parse_jobs_from_response(SAMPLE_RESPONSE)
        assert len(jobs) == 2
        assert total == 2
        assert jobs[0].company_name == "Oracle"
        assert jobs[0].job_title == "Software Developer"
        assert jobs[0].location == "Mumbai, MH, IN"
        assert "230100001" in jobs[0].job_link

    def test_empty_response(self):
        jobs, total = _parse_jobs_from_response(EMPTY_RESPONSE)
        assert len(jobs) == 0
        assert total == 0

    def test_description_truncated_to_500(self):
        data = {"items": [{"TotalJobsCount": 1, "requisitionList": [
            {"Id": "1", "Title": "Dev", "PrimaryLocation": "", "ShortDescriptionStr": "x" * 600}
        ]}]}
        jobs, _ = _parse_jobs_from_response(data)
        assert len(jobs[0].job_description) == 500


class TestOracleScraper:
    def test_source_name(self):
        scraper = OracleScraper("https://careers.oracle.com/...")
        assert scraper.source_name() == "oracle"

    @patch("src.scrapers.oracle_careers.httpx")
    def test_fetch_jobs(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_resp

        scraper = OracleScraper("https://careers.oracle.com/...")
        jobs = scraper.fetch_jobs()
        assert len(jobs) == 2
        assert jobs[0].location == "Mumbai, MH, IN"
