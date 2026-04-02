"""Playwright-based scraper base class for JavaScript-rendered career pages."""
import logging
from abc import abstractmethod
from contextlib import contextmanager

from playwright.sync_api import sync_playwright, Browser, Page

from src.scrapers.base import BaseScraper, RawJob

logger = logging.getLogger("jobsearch.scrapers.playwright")

DEFAULT_TIMEOUT = 30_000  # 30 seconds
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}


class PlaywrightScraper(BaseScraper):
    """Base class for scrapers that need a real browser.

    Subclasses implement source_name() and extract_jobs(page).
    The browser lifecycle is handled here.
    """

    def fetch_jobs(self) -> list[RawJob]:
        with self._browser_page() as page:
            logger.info("Navigating to %s", self.url)
            page.goto(self.url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
            return self.extract_jobs(page)

    @abstractmethod
    def extract_jobs(self, page: Page) -> list[RawJob]:
        """Extract jobs from a fully loaded page. Subclasses implement this."""
        ...

    @contextmanager
    def _browser_page(self):
        """Context manager that yields a Playwright page with proper cleanup."""
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1280, "height": 720},
        )
        page = context.new_page()
        try:
            yield page
        finally:
            context.close()
            browser.close()
            pw.stop()
