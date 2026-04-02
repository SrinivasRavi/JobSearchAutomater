"""Visa scraper adapter — SmartRecruiters public JSON API."""
import logging

import httpx

from src.scrapers.base import BaseScraper, RawJob
from src.scrapers.registry import register_adapter

logger = logging.getLogger("jobsearch.scrapers.visa")

API_BASE = "https://api.smartrecruiters.com/v1/companies/visa/postings"
MAX_PAGES = 10
PAGE_SIZE = 100
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _parse_jobs_from_response(data: dict) -> list[RawJob]:
    """Parse SmartRecruiters API response into RawJob list."""
    jobs = []
    for item in data.get("content", []):
        location = item.get("location", {})
        loc_str = ", ".join(filter(None, [
            location.get("city", ""),
            location.get("region", ""),
            location.get("country", ""),
        ]))

        job_id = item.get("id", "")
        name = item.get("name", "")
        slug = name.lower().replace(" ", "-").replace(",", "").replace(".", "")
        company_id = item.get("company", {}).get("identifier", "Visa")
        job_link = f"https://jobs.smartrecruiters.com/{company_id}/{job_id}-{slug}"

        jobs.append(RawJob(
            company_name="Visa",
            job_title=name,
            job_description=f"{name} - {loc_str}" if loc_str else name,
            job_link=job_link,
        ))
    return jobs


class VisaScraper(BaseScraper):
    """Scrapes Visa careers via SmartRecruiters public API."""

    def source_name(self) -> str:
        return "visa"

    def fetch_jobs(self) -> list[RawJob]:
        all_jobs: list[RawJob] = []
        offset = 0

        for page in range(MAX_PAGES):
            params = {
                "city": "Mumbai",
                "limit": PAGE_SIZE,
                "offset": offset,
            }

            logger.info("Fetching Visa page %d: offset=%d", page + 1, offset)
            response = httpx.get(API_BASE, params=params,
                                 headers=HEADERS, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            page_jobs = _parse_jobs_from_response(data)
            all_jobs.extend(page_jobs)

            total = data.get("totalFound", 0)
            offset += PAGE_SIZE
            if offset >= total or len(page_jobs) == 0:
                break

        logger.info("Visa scraper found %d jobs total", len(all_jobs))
        return all_jobs


register_adapter("visa", VisaScraper)
