"""JPMorgan scraper adapter — Oracle HCM REST API (no browser needed)."""
import logging
from urllib.parse import quote

import httpx

from src.scrapers.base import BaseScraper, RawJob
from src.scrapers.registry import register_adapter

logger = logging.getLogger("jobsearch.scrapers.jpmorgan")

API_BASE = "https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
JOB_URL_BASE = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job"
SITE_NUMBER = "CX_1001"
MAX_PAGES = 20
PAGE_SIZE = 25
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _parse_jobs_from_response(data: dict) -> tuple[list[RawJob], int]:
    """Parse Oracle HCM API response into RawJob list and total count."""
    jobs = []
    items = data.get("items", [])
    if not items:
        return [], 0

    item = items[0]
    total = item.get("TotalJobsCount", 0)

    for req in item.get("requisitionList", []):
        title = req.get("Title", "")
        job_id = req.get("Id", "")
        location = req.get("PrimaryLocation", "")
        short_desc = req.get("ShortDescriptionStr", "")
        job_link = f"{JOB_URL_BASE}/{job_id}" if job_id else ""

        jobs.append(RawJob(
            company_name="JPMorgan Chase",
            job_title=title,
            job_description=short_desc[:500] if short_desc else title,
            job_link=job_link,
            location=location,
        ))
    return jobs, total


class JPMorganScraper(BaseScraper):
    """Scrapes JPMorgan via Oracle HCM REST API."""

    def source_name(self) -> str:
        return "jpmorgan"

    def fetch_jobs(self) -> list[RawJob]:
        all_jobs: list[RawJob] = []
        offset = 0

        for page in range(MAX_PAGES):
            finder = (
                f"findReqs;siteNumber={SITE_NUMBER},"
                f"limit={PAGE_SIZE},"
                f"offset={offset},"
                f"keyword=Software Engineer,"
                f"sortBy=POSTING_DATES_DESC"
            )
            params = {
                "onlyData": "true",
                "expand": "requisitionList.secondaryLocations",
                "finder": finder,
            }

            logger.info("Fetching JPMorgan page %d: offset=%d", page + 1, offset)
            response = httpx.get(API_BASE, params=params,
                                 headers=HEADERS, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            page_jobs, total = _parse_jobs_from_response(data)
            if not page_jobs:
                break
            all_jobs.extend(page_jobs)

            offset += PAGE_SIZE
            if offset >= total:
                break

        logger.info("JPMorgan scraper found %d jobs total", len(all_jobs))
        return all_jobs


register_adapter("jpmorgan", JPMorganScraper)
