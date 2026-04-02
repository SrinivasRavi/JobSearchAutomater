"""Google scraper adapter — fully client-rendered SPA with Playwright."""
import logging

from playwright.sync_api import Page

from src.scrapers.base import RawJob
from src.scrapers.playwright_base import PlaywrightScraper
from src.scrapers.registry import register_adapter

logger = logging.getLogger("jobsearch.scrapers.google")

MAX_PAGES = 10


class GoogleScraper(PlaywrightScraper):
    """Scrapes Google careers via Playwright (client-rendered SPA)."""

    def source_name(self) -> str:
        return "google"

    def extract_jobs(self, page: Page) -> list[RawJob]:
        page.wait_for_selector("li.lLd3Je", timeout=20_000)
        page.wait_for_timeout(2000)

        all_jobs: list[RawJob] = []

        for page_num in range(MAX_PAGES):
            jobs = self._extract_page_jobs(page)
            if not jobs:
                break
            all_jobs.extend(jobs)
            logger.info("Google page %d: %d jobs", page_num + 1, len(jobs))

            next_btn = page.query_selector(
                "button[aria-label='Next page'], a[aria-label='Next']"
            )
            if not next_btn or not next_btn.is_enabled():
                break
            next_btn.click()
            page.wait_for_timeout(3000)

        logger.info("Google scraper found %d jobs total", len(all_jobs))
        return all_jobs

    def _extract_page_jobs(self, page: Page) -> list[RawJob]:
        cards = page.query_selector_all("li.lLd3Je")
        jobs = []
        for card in cards:
            title_el = card.query_selector("h3, h2, [class*='title'], [class*='Title']")
            title = title_el.inner_text().strip() if title_el else card.inner_text().strip()[:100]
            if not title or len(title) < 3:
                continue

            location_el = card.query_selector(
                "span[class*='r0wTof'], [class*='location'], [class*='Location']"
            )
            location = location_el.inner_text().strip() if location_el else ""

            href = ""
            link_el = card.query_selector("a[href]")
            if link_el:
                href = link_el.get_attribute("href") or ""

            if href and not href.startswith("http"):
                href = f"https://www.google.com{href}"

            jobs.append(RawJob(
                company_name="Google",
                job_title=title,
                job_description=f"{title} - {location}" if location else title,
                job_link=href,
                location=location,
            ))
        return jobs


register_adapter("google", GoogleScraper)
