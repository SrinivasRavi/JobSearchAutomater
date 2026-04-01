"""Tests for Citi scraper adapter."""
import pytest
from unittest.mock import patch, MagicMock

from src.scrapers.citi import CitiScraper, _parse_jobs_from_html
from src.scrapers.base import RawJob

SAMPLE_HTML = """
<html><body>
<ul>
  <li class="sr-job-item">
    <h3 class="sr-job-item__title">
      <a class="sr-job-item__link" href="/job/mumbai/software-engineer-java/287/93460215712">Software Engineer - Java</a>
    </h3>
    <span class="sr-job-item__facet sr-job-item__facet-icon sr-job-location">Mumbai, Maharashtra, India</span>
  </li>
  <li class="sr-job-item">
    <h3 class="sr-job-item__title">
      <a class="sr-job-item__link" href="/job/pune/senior-software-engineer/287/93460215632">Senior Software Engineer</a>
    </h3>
    <span class="sr-job-item__facet sr-job-item__facet-icon sr-job-location">Pune, Maharashtra, India</span>
  </li>
</ul>
</body></html>
"""

EMPTY_HTML = """<html><body><ul></ul></body></html>"""


class TestParseCitiHtml:
    def test_parses_jobs(self):
        jobs = _parse_jobs_from_html(SAMPLE_HTML, "https://jobs.citi.com")
        assert len(jobs) == 2
        assert jobs[0].company_name == "Citi"
        assert jobs[0].job_title == "Software Engineer - Java"
        assert "jobs.citi.com" in jobs[0].job_link

    def test_empty_html(self):
        jobs = _parse_jobs_from_html(EMPTY_HTML, "https://jobs.citi.com")
        assert len(jobs) == 0

    def test_job_link_is_absolute(self):
        jobs = _parse_jobs_from_html(SAMPLE_HTML, "https://jobs.citi.com")
        for job in jobs:
            assert job.job_link.startswith("https://")


class TestCitiScraper:
    def test_source_name(self):
        scraper = CitiScraper("https://jobs.citi.com/category/software-engineer-jobs/287/8644128/1")
        assert scraper.source_name() == "citi"

    @patch("src.scrapers.citi.httpx")
    def test_fetch_jobs(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_HTML
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_resp

        scraper = CitiScraper("https://jobs.citi.com/category/software-engineer-jobs/287/8644128/1")
        jobs = scraper.fetch_jobs()
        assert len(jobs) == 2

    @patch("src.scrapers.citi.httpx")
    def test_handles_error(self, mock_httpx):
        mock_httpx.get.side_effect = ConnectionError("timeout")
        scraper = CitiScraper("https://jobs.citi.com/category/software-engineer-jobs/287/8644128/1")
        result = scraper.scrape()
        assert result.jobs == []
        assert len(result.errors) == 1
