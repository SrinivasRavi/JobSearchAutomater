"""Nasdaq scraper adapter — Workday CXS REST API (no browser needed)."""
import logging

import httpx

from src.scrapers.base import BaseScraper, RawJob
from src.scrapers.registry import register_adapter

logger = logging.getLogger("jobsearch.scrapers.nasdaq")

API_URL = "https://nasdaq.wd1.myworkdayjobs.com/wday/cxs/nasdaq/Global_External_Site/jobs"
JOB_URL_BASE = "https://nasdaq.wd1.myworkdayjobs.com/Global_External_Site"
MAX_PAGES = 10
PAGE_SIZE = 20
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _parse_jobs_from_response(data: dict) -> tuple[list[RawJob], int]:
    """Parse Workday CXS API response into RawJob list and total count."""
    jobs = []
    total = data.get("total", 0)

    for posting in data.get("jobPostings", []):
        title = posting.get("title", "")
        external_path = posting.get("externalPath", "")
        location = posting.get("locationsText", "")
        bullet_fields = posting.get("bulletFields", [])
        req_id = bullet_fields[0] if bullet_fields else ""

        job_link = f"{JOB_URL_BASE}{external_path}" if external_path else ""
        desc = f"{title} - {location}" if location else title
        if req_id:
            desc = f"{desc} ({req_id})"

        jobs.append(RawJob(
            company_name="Nasdaq",
            job_title=title,
            job_description=desc,
            job_link=job_link,
            location=location,
        ))
    return jobs, total


class NasdaqScraper(BaseScraper):
    """Scrapes Nasdaq via Workday CXS REST API."""

    def source_name(self) -> str:
        return "nasdaq"

    def fetch_jobs(self) -> list[RawJob]:
        all_jobs: list[RawJob] = []
        offset = 0

        for page in range(MAX_PAGES):
            body = {
                "appliedFacets": {
                    "Location_Country": ["c4f78be1a8f14da0ab49ce1162348a5e"],
                    "locations": [
                        "84ab8350a70e10019c78e4295b9b0000",
                        "b638d7611d08100143bd56aa78670000",
                    ],
                    "timeType": ["c5d5bf172e3c019da4ea33754c384e00"],
                },
                "limit": PAGE_SIZE,
                "offset": offset,
                "searchText": "software engineer",
            }

            logger.info("Fetching Nasdaq page %d: offset=%d", page + 1, offset)
            response = httpx.post(API_URL, json=body,
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

        logger.info("Nasdaq scraper found %d jobs total", len(all_jobs))
        return all_jobs


register_adapter("nasdaq", NasdaqScraper)
