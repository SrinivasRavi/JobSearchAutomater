"""Tests for JPMorgan scraper adapter (Oracle HCM REST API)."""
from unittest.mock import patch, MagicMock

from src.scrapers.jpmorgan import JPMorganScraper, _parse_jobs_from_response
from src.scrapers.base import RawJob


SAMPLE_RESPONSE = {
    "items": [{
        "TotalJobsCount": 2,
        "requisitionList": [
            {
                "Id": "210500001",
                "Title": "Software Engineer II",
                "PrimaryLocation": "Mumbai, MH, IN",
                "ShortDescriptionStr": "Build scalable backend systems.",
            },
            {
                "Id": "210500002",
                "Title": "Senior Java Developer",
                "PrimaryLocation": "Pune, MH, IN",
                "ShortDescriptionStr": "Design microservices architecture.",
            },
        ],
    }],
}

EMPTY_RESPONSE = {"items": [{"TotalJobsCount": 0, "requisitionList": []}]}
NO_ITEMS_RESPONSE = {"items": []}


class TestParseJobsFromResponse:
    def test_parses_jobs(self):
        jobs, total = _parse_jobs_from_response(SAMPLE_RESPONSE)
        assert len(jobs) == 2
        assert total == 2
        assert jobs[0].company_name == "JPMorgan Chase"
        assert jobs[0].job_title == "Software Engineer II"
        assert jobs[0].location == "Mumbai, MH, IN"
        assert "210500001" in jobs[0].job_link

    def test_empty_requisition_list(self):
        jobs, total = _parse_jobs_from_response(EMPTY_RESPONSE)
        assert len(jobs) == 0
        assert total == 0

    def test_no_items(self):
        jobs, total = _parse_jobs_from_response(NO_ITEMS_RESPONSE)
        assert len(jobs) == 0
        assert total == 0

    def test_missing_fields_handled(self):
        data = {"items": [{"TotalJobsCount": 1, "requisitionList": [
            {"Title": "Analyst", "Id": "", "PrimaryLocation": "", "ShortDescriptionStr": ""}
        ]}]}
        jobs, total = _parse_jobs_from_response(data)
        assert len(jobs) == 1
        assert jobs[0].job_title == "Analyst"
        assert jobs[0].job_link == ""
        assert jobs[0].job_description == "Analyst"


class TestJPMorganScraper:
    def test_source_name(self):
        scraper = JPMorganScraper("https://jpmc.fa.oraclecloud.com/...")
        assert scraper.source_name() == "jpmorgan"

    @patch("src.scrapers.jpmorgan.httpx")
    def test_fetch_jobs_single_page(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = SAMPLE_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_resp

        scraper = JPMorganScraper("https://jpmc.fa.oraclecloud.com/...")
        jobs = scraper.fetch_jobs()
        assert len(jobs) == 2
        assert jobs[1].location == "Pune, MH, IN"

    @patch("src.scrapers.jpmorgan.httpx")
    def test_fetch_jobs_pagination(self, mock_httpx):
        page1 = {"items": [{"TotalJobsCount": 30, "requisitionList": [
            {"Id": str(i), "Title": f"Job {i}", "PrimaryLocation": "Mumbai", "ShortDescriptionStr": ""}
            for i in range(25)
        ]}]}
        page2 = {"items": [{"TotalJobsCount": 30, "requisitionList": [
            {"Id": str(i), "Title": f"Job {i}", "PrimaryLocation": "Mumbai", "ShortDescriptionStr": ""}
            for i in range(25, 30)
        ]}]}

        mock_resp1 = MagicMock()
        mock_resp1.json.return_value = page1
        mock_resp1.raise_for_status = MagicMock()
        mock_resp2 = MagicMock()
        mock_resp2.json.return_value = page2
        mock_resp2.raise_for_status = MagicMock()
        mock_httpx.get.side_effect = [mock_resp1, mock_resp2]

        scraper = JPMorganScraper("https://jpmc.fa.oraclecloud.com/...")
        jobs = scraper.fetch_jobs()
        assert len(jobs) == 30
