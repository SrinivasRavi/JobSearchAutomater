"""Citi scraper adapter — HTML parsing from TalentBrew/Radancy platform."""
import logging
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, RawJob
from src.scrapers.registry import register_adapter

logger = logging.getLogger("jobsearch.scrapers.citi")

MAX_PAGES = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html",
}


def _parse_jobs_from_html(html: str, base_url: str) -> list[RawJob]:
    """Parse Citi job listings from server-rendered HTML."""
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    cards = soup.find_all("li", class_="sr-job-item")
    for card in cards:
        title_link = card.find("a", class_="sr-job-item__link")
        if not title_link:
            continue

        title = title_link.get_text(strip=True)
        href = title_link.get("href", "")
        job_link = urljoin(base_url, href) if href else ""

        location_el = card.find("span", class_="sr-job-location")
        location = location_el.get_text(strip=True) if location_el else ""

        description = f"{title} - {location}" if location else title

        jobs.append(RawJob(
            company_name="Citi",
            job_title=title,
            job_description=description,
            job_link=job_link,
        ))

    return jobs


class CitiScraper(BaseScraper):
    """Scrapes Citi careers via server-rendered HTML."""

    def source_name(self) -> str:
        return "citi"

    def fetch_jobs(self) -> list[RawJob]:
        parsed = urlparse(self.url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        all_jobs: list[RawJob] = []
        current_url = self.url

        for page in range(MAX_PAGES):
            logger.info("Fetching Citi page %d: %s", page + 1, current_url)

            response = httpx.get(current_url, headers=HEADERS,
                                 follow_redirects=True, timeout=30.0)
            response.raise_for_status()

            page_jobs = _parse_jobs_from_html(response.text, base_url)
            if not page_jobs:
                break
            all_jobs.extend(page_jobs)

            soup = BeautifulSoup(response.text, "lxml")
            next_link = soup.find("a", class_="next")
            if next_link and next_link.get("href"):
                current_url = urljoin(base_url, next_link["href"])
            else:
                break

        logger.info("Citi scraper found %d jobs total", len(all_jobs))
        return all_jobs


register_adapter("citi", CitiScraper)
