"""Tests for Barclays scraper adapter."""
import pytest
from unittest.mock import patch, MagicMock

from src.scrapers.barclays import BarclaysScraper, _parse_jobs_from_html
from src.scrapers.base import RawJob

SAMPLE_HTML = """
<html><body>
<div class="no-bullet-list job-list--card search-results--card auto-grid auto-grid--card-items mb-0">
  <div class="list-item list-item--card fs-column fs-top round-corners bg--pale-blue-light p-1 text--black">
    <a class="headline-3 job-title--link text--black" href="/job/mumbai/software-engineer/13015/86239313104">Software Engineer</a>
    <div class="job-location">Mumbai, India</div>
    <div class="bg--white round-corners--small job-date">
      <time>07 Jan</time>
    </div>
  </div>
  <div class="list-item list-item--card fs-column fs-top round-corners bg--pale-blue-light p-1 text--black">
    <a class="headline-3 job-title--link text--black" href="/job/pune/senior-software-engineer/13015/87359957248">Senior Software Engineer</a>
    <div class="job-location">Pune, India</div>
    <div class="bg--white round-corners--small job-date">
      <time>26 Jan</time>
    </div>
  </div>
</div>
</body></html>
"""

EMPTY_HTML = """
<html><body>
<div class="search-results--card"></div>
</body></html>
"""


class TestParseBarclaysHtml:
    def test_parses_jobs(self):
        jobs = _parse_jobs_from_html(SAMPLE_HTML, "https://search.jobs.barclays")
        assert len(jobs) == 2
        assert jobs[0].company_name == "Barclays"
        assert jobs[0].job_title == "Software Engineer"
        assert "search.jobs.barclays" in jobs[0].job_link
        assert jobs[0].location == "Mumbai, India"
        assert jobs[1].job_title == "Senior Software Engineer"
        assert jobs[1].location == "Pune, India"

    def test_empty_html(self):
        jobs = _parse_jobs_from_html(EMPTY_HTML, "https://search.jobs.barclays")
        assert len(jobs) == 0

    def test_job_link_is_absolute(self):
        jobs = _parse_jobs_from_html(SAMPLE_HTML, "https://search.jobs.barclays")
        for job in jobs:
            assert job.job_link.startswith("https://")


class TestBarclaysScraper:
    def test_source_name(self):
        scraper = BarclaysScraper("https://search.jobs.barclays/search-jobs?k=test")
        assert scraper.source_name() == "barclays"

    @patch("src.scrapers.barclays.httpx")
    def test_fetch_jobs(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_HTML
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_resp

        scraper = BarclaysScraper("https://search.jobs.barclays/search-jobs?k=software+engineer")
        jobs = scraper.fetch_jobs()
        assert len(jobs) == 2

    @patch("src.scrapers.barclays.httpx")
    def test_handles_error(self, mock_httpx):
        mock_httpx.get.side_effect = ConnectionError("timeout")
        scraper = BarclaysScraper("https://search.jobs.barclays/search-jobs?k=test")
        result = scraper.scrape()
        assert result.jobs == []
        assert len(result.errors) == 1
