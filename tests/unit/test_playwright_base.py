"""Tests for Playwright base scraper."""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from src.scrapers.playwright_base import PlaywrightScraper
from src.scrapers.base import RawJob


class FakePlaywrightScraper(PlaywrightScraper):
    def source_name(self) -> str:
        return "fake_pw"

    def extract_jobs(self, page) -> list[RawJob]:
        return [
            RawJob(
                company_name="TestCorp",
                job_title="Engineer",
                job_description="Build things",
                job_link="https://example.com/job/1",
                location="Mumbai",
            )
        ]


class FailingPlaywrightScraper(PlaywrightScraper):
    def source_name(self) -> str:
        return "failing_pw"

    def extract_jobs(self, page) -> list[RawJob]:
        raise ValueError("Parse error")


class TestPlaywrightScraper:
    def test_source_name(self):
        scraper = FakePlaywrightScraper("https://example.com")
        assert scraper.source_name() == "fake_pw"

    @patch("src.scrapers.playwright_base.sync_playwright")
    def test_fetch_jobs_launches_browser(self, mock_pw_fn):
        mock_pw = MagicMock()
        mock_pw_fn.return_value.start.return_value = mock_pw
        mock_browser = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page

        scraper = FakePlaywrightScraper("https://example.com/jobs")
        jobs = scraper.fetch_jobs()

        assert len(jobs) == 1
        assert jobs[0].job_title == "Engineer"
        assert jobs[0].location == "Mumbai"
        mock_pw.chromium.launch.assert_called_once_with(headless=True)
        mock_page.goto.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()

    @patch("src.scrapers.playwright_base.sync_playwright")
    def test_scrape_captures_errors(self, mock_pw_fn):
        mock_pw = MagicMock()
        mock_pw_fn.return_value.start.return_value = mock_pw
        mock_browser = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page

        scraper = FailingPlaywrightScraper("https://example.com/jobs")
        result = scraper.scrape()

        assert result.jobs == []
        assert len(result.errors) == 1
        assert "Parse error" in result.errors[0]
        # Browser should still be cleaned up
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()

    @patch("src.scrapers.playwright_base.sync_playwright")
    def test_browser_cleanup_on_success(self, mock_pw_fn):
        mock_pw = MagicMock()
        mock_pw_fn.return_value.start.return_value = mock_pw
        mock_browser = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page

        scraper = FakePlaywrightScraper("https://example.com/jobs")
        scraper.fetch_jobs()

        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_pw.stop.assert_called_once()
