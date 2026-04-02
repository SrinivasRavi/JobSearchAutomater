"""Goldman Sachs scraper adapter — React SPA with Playwright."""
import logging

from playwright.sync_api import Page

from src.scrapers.base import RawJob
from src.scrapers.playwright_base import PlaywrightScraper
from src.scrapers.registry import register_adapter

logger = logging.getLogger("jobsearch.scrapers.goldman_sachs")

MAX_PAGES = 15


class GoldmanSachsScraper(PlaywrightScraper):
    """Scrapes Goldman Sachs careers via Playwright (higher.gs.com)."""

    def source_name(self) -> str:
        return "goldman_sachs"

    def extract_jobs(self, page: Page) -> list[RawJob]:
        try:
            page.wait_for_selector("a[href^='/roles/']", timeout=20_000)
        except Exception:
            logger.info("Goldman Sachs: no job listings found on page")
            return []
        page.wait_for_timeout(2000)

        all_jobs: list[RawJob] = []

        for page_num in range(MAX_PAGES):
            jobs = self._extract_page_jobs(page)
            if not jobs:
                break
            all_jobs.extend(jobs)
            logger.info("Goldman Sachs page %d: %d jobs", page_num + 1, len(jobs))

            next_btn = page.query_selector(
                "a[aria-label='Goto next page'], "
                "button[aria-label='Next page'], "
                "[aria-label='Go to next page']"
            )
            if not next_btn or not next_btn.is_enabled():
                break
            next_btn.click()
            page.wait_for_timeout(3000)

        logger.info("Goldman Sachs scraper found %d jobs total", len(all_jobs))
        return all_jobs

    def _extract_page_jobs(self, page: Page) -> list[RawJob]:
        cards = page.query_selector_all("a[href^='/roles/']")
        jobs = []
        seen_hrefs = set()

        for card in cards:
            href = card.get_attribute("href") or ""
            if not href or href in seen_hrefs:
                continue
            seen_hrefs.add(href)

            title_el = card.query_selector(".gs-text, span[class*='text-root']")
            title = title_el.inner_text().strip() if title_el else card.inner_text().strip()[:100]
            if not title or len(title) < 3:
                continue

            location_el = card.query_selector("[data-testid='location'] .gs-text, [data-testid='location'] span")
            location = location_el.inner_text().strip() if location_el else ""

            full_url = f"https://higher.gs.com{href}" if not href.startswith("http") else href

            jobs.append(RawJob(
                company_name="Goldman Sachs",
                job_title=title,
                job_description=f"{title} - {location}" if location else title,
                job_link=full_url,
                location=location,
            ))
        return jobs


register_adapter("goldman_sachs", GoldmanSachsScraper)
