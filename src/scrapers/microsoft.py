"""Microsoft scraper adapter — Eightfold SPA with Playwright."""
import logging

from playwright.sync_api import Page

from src.scrapers.base import RawJob
from src.scrapers.playwright_base import PlaywrightScraper
from src.scrapers.registry import register_adapter

logger = logging.getLogger("jobsearch.scrapers.microsoft")

MAX_PAGES = 10


class MicrosoftScraper(PlaywrightScraper):
    """Scrapes Microsoft careers via Playwright (Eightfold.ai platform)."""

    def source_name(self) -> str:
        return "microsoft"

    def extract_jobs(self, page: Page) -> list[RawJob]:
        page.wait_for_selector(
            "[class*='position'], [class*='job-card'], [class*='JobCard'], "
            "[data-ph-at-id='jobs-list']",
            timeout=15_000,
        )
        page.wait_for_timeout(2000)

        all_jobs: list[RawJob] = []

        for page_num in range(MAX_PAGES):
            jobs = self._extract_page_jobs(page)
            if not jobs:
                break
            all_jobs.extend(jobs)
            logger.info("Microsoft page %d: %d jobs", page_num + 1, len(jobs))

            next_btn = page.query_selector(
                "button[aria-label='next'], [class*='pagination'] button:last-child, "
                "a[class*='next']"
            )
            if not next_btn or not next_btn.is_enabled():
                break
            next_btn.click()
            page.wait_for_timeout(3000)

        logger.info("Microsoft scraper found %d jobs total", len(all_jobs))
        return all_jobs

    def _extract_page_jobs(self, page: Page) -> list[RawJob]:
        cards = page.query_selector_all(
            "[class*='position-card'], [class*='job-card'], "
            "[class*='JobCard'], [data-ph-at-id='job-link']"
        )
        if not cards:
            cards = page.query_selector_all("a[href*='/careers/']")

        jobs = []
        for card in cards:
            title_el = card.query_selector(
                "[class*='position-title'], [class*='job-title'], h3, h2"
            )
            title = title_el.inner_text().strip() if title_el else card.inner_text().strip()[:100]
            if not title:
                continue

            location_el = card.query_selector(
                "[class*='location'], [class*='Location']"
            )
            location = location_el.inner_text().strip() if location_el else ""

            href = card.get_attribute("href") or ""
            if not href:
                link_el = card.query_selector("a[href]")
                href = link_el.get_attribute("href") if link_el else ""

            if href and not href.startswith("http"):
                href = f"https://apply.careers.microsoft.com{href}"

            jobs.append(RawJob(
                company_name="Microsoft",
                job_title=title,
                job_description=f"{title} - {location}" if location else title,
                job_link=href,
                location=location,
            ))
        return jobs


register_adapter("microsoft", MicrosoftScraper)
