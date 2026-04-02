"""Bank of America scraper adapter — Adobe AEM with Playwright."""
import logging

from playwright.sync_api import Page

from src.scrapers.base import RawJob
from src.scrapers.playwright_base import PlaywrightScraper
from src.scrapers.registry import register_adapter

logger = logging.getLogger("jobsearch.scrapers.bofa")

MAX_PAGES = 10


class BofAScraper(PlaywrightScraper):
    """Scrapes Bank of America careers via Playwright (Adobe AEM)."""

    def source_name(self) -> str:
        return "bofa"

    def extract_jobs(self, page: Page) -> list[RawJob]:
        page.wait_for_selector(
            "[class*='job-result'], [class*='search-result'], "
            "[class*='job-card'], .results-list",
            timeout=20_000,
        )
        page.wait_for_timeout(3000)

        all_jobs: list[RawJob] = []

        for page_num in range(MAX_PAGES):
            jobs = self._extract_page_jobs(page)
            if not jobs:
                break
            all_jobs.extend(jobs)
            logger.info("BofA page %d: %d jobs", page_num + 1, len(jobs))

            next_btn = page.query_selector(
                "a[class*='next'], button[class*='next'], "
                "[aria-label*='Next'], [class*='pagination'] a:last-child"
            )
            if not next_btn or not next_btn.is_visible():
                break
            next_btn.click()
            page.wait_for_timeout(3000)

        logger.info("BofA scraper found %d jobs total", len(all_jobs))
        return all_jobs

    def _extract_page_jobs(self, page: Page) -> list[RawJob]:
        cards = page.query_selector_all(
            "[class*='job-result'], [class*='search-result'], "
            "[class*='job-card'], .results-list li"
        )
        jobs = []
        for card in cards:
            title_el = card.query_selector("h2, h3, a[class*='title'], [class*='title']")
            title = title_el.inner_text().strip() if title_el else ""
            if not title:
                continue

            location_el = card.query_selector("[class*='location']")
            location = location_el.inner_text().strip() if location_el else ""

            href = ""
            link_el = card.query_selector("a[href]")
            if link_el:
                href = link_el.get_attribute("href") or ""
            if href and not href.startswith("http"):
                href = f"https://careers.bankofamerica.com{href}"

            jobs.append(RawJob(
                company_name="Bank of America",
                job_title=title,
                job_description=f"{title} - {location}" if location else title,
                job_link=href,
                location=location,
            ))
        return jobs


register_adapter("bofa", BofAScraper)
