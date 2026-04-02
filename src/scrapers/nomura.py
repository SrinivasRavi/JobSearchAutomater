"""Nomura scraper adapter — HTML table parsing."""
import logging
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, RawJob
from src.scrapers.registry import register_adapter

logger = logging.getLogger("jobsearch.scrapers.nomura")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html",
}


def _parse_jobs_from_html(html: str, base_url: str) -> list[RawJob]:
    """Parse Nomura job listings from HTML table rows."""
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    for tr in soup.find_all("tr", class_="data-row"):
        link = tr.find("a", class_="jobTitle-link")
        if not link:
            continue

        title = link.get_text(strip=True)
        href = link.get("href", "")
        job_link = urljoin(base_url, href)

        tds = tr.find_all("td")
        location = tds[2].get_text(strip=True) if len(tds) > 2 else ""

        jobs.append(RawJob(
            company_name="Nomura",
            job_title=title,
            job_description=f"{title} - {location}" if location else title,
            job_link=job_link,
        ))

    return jobs


class NomuraScraper(BaseScraper):
    """Scrapes Nomura careers via HTML table parsing."""

    def source_name(self) -> str:
        return "nomura"

    def fetch_jobs(self) -> list[RawJob]:
        logger.info("Fetching Nomura: %s", self.url)

        response = httpx.get(self.url, headers=HEADERS,
                             follow_redirects=True, timeout=30.0)
        response.raise_for_status()

        base_url = "https://careers.nomura.com"
        jobs = _parse_jobs_from_html(response.text, base_url)
        logger.info("Nomura scraper found %d jobs", len(jobs))
        return jobs


register_adapter("nomura", NomuraScraper)
