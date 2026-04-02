"""Tests for Nomura scraper adapter."""
import pytest
from unittest.mock import patch, MagicMock

from src.scrapers.nomura import NomuraScraper, _parse_jobs_from_html
from src.scrapers.base import RawJob

SAMPLE_HTML = """
<html><body>
<table>
  <tr class="data-row">
    <td><a class="jobTitle-link" href="/Nomura/job/Mumbai-Lead-Software-Engineer/1340801300/">Lead Software Engineer</a></td>
    <td>Group Technology</td>
    <td>Mumbai, IN</td>
  </tr>
  <tr class="data-row">
    <td><a class="jobTitle-link" href="/Nomura/job/Mumbai-Software-Engineer/1360264000/">Software Engineer</a></td>
    <td>Group Technology</td>
    <td>Mumbai, IN</td>
  </tr>
</table>
</body></html>
"""


class TestParseNomuraHtml:
    def test_parses_jobs(self):
        jobs = _parse_jobs_from_html(SAMPLE_HTML, "https://careers.nomura.com")
        assert len(jobs) == 2
        assert jobs[0].company_name == "Nomura"
        assert jobs[0].job_title == "Lead Software Engineer"
        assert "careers.nomura.com" in jobs[0].job_link

    def test_empty_html(self):
        jobs = _parse_jobs_from_html("<html><body></body></html>", "https://careers.nomura.com")
        assert len(jobs) == 0


class TestNomuraScraper:
    def test_source_name(self):
        scraper = NomuraScraper("https://careers.nomura.com/Nomura/go/test/1/")
        assert scraper.source_name() == "nomura"

    @patch("src.scrapers.nomura.httpx")
    def test_fetch_jobs(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_HTML
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_resp

        scraper = NomuraScraper("https://careers.nomura.com/Nomura/go/test/1/")
        jobs = scraper.fetch_jobs()
        assert len(jobs) == 2
