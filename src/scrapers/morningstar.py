"""Morningstar scraper adapter — Phenom People platform, embedded JS data."""
import json
import logging
import re
from urllib.parse import urlparse, urlencode, parse_qs

import httpx

from src.scrapers.base import BaseScraper, RawJob
from src.scrapers.registry import register_adapter

logger = logging.getLogger("jobsearch.scrapers.morningstar")

MAX_PAGES = 10
PAGE_SIZE = 25
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html",
}

_PHAPP_START = re.compile(r"phApp\.ddo\s*=\s*")


def _extract_jobs_from_html(html: str) -> tuple[list[dict], int]:
    """Extract job dicts and totalHits from embedded phApp.ddo object."""
    match = _PHAPP_START.search(html)
    if not match:
        return [], 0

    try:
        decoder = json.JSONDecoder()
        ddo, _ = decoder.raw_decode(html, match.end())
    except (json.JSONDecodeError, ValueError):
        return [], 0

    search_data = ddo.get("eagerLoadRefineSearch", {})
    jobs = search_data.get("data", {}).get("jobs", [])
    total_hits = search_data.get("totalHits", 0)
    return jobs, total_hits


def _parse_jobs(raw_jobs: list[dict]) -> list[RawJob]:
    """Convert raw job dicts to RawJob objects."""
    jobs = []
    for item in raw_jobs:
        title = item.get("title", "")
        job_id = item.get("jobId", "")
        location = item.get("location", "")
        description = item.get("descriptionTeaser", title)
        apply_url = item.get("applyUrl", "")

        if not apply_url and job_id:
            apply_url = f"https://careers.morningstar.com/us/en/job/{job_id}"

        jobs.append(RawJob(
            company_name="Morningstar",
            job_title=title,
            job_description=description[:500] if description else title,
            job_link=apply_url,
            location=location,
        ))
    return jobs


class MorningstarScraper(BaseScraper):
    """Scrapes Morningstar careers via Phenom People embedded JS data."""

    def source_name(self) -> str:
        return "morningstar"

    def fetch_jobs(self) -> list[RawJob]:
        parsed = urlparse(self.url)
        base_path = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        base_params = parse_qs(parsed.query)
        flat_params = {k: v[0] for k, v in base_params.items()}

        all_jobs: list[RawJob] = []
        offset = 0

        for page in range(MAX_PAGES):
            flat_params["from"] = str(offset)
            flat_params["size"] = str(PAGE_SIZE)
            page_url = f"{base_path}?{urlencode(flat_params)}"

            logger.info("Fetching Morningstar page %d: offset=%d", page + 1, offset)
            response = httpx.get(page_url, headers=HEADERS,
                                 follow_redirects=True, timeout=30.0)
            response.raise_for_status()

            raw_jobs, total_hits = _extract_jobs_from_html(response.text)
            if not raw_jobs:
                break

            page_jobs = _parse_jobs(raw_jobs)
            all_jobs.extend(page_jobs)

            offset += PAGE_SIZE
            if offset >= total_hits:
                break

        logger.info("Morningstar scraper found %d jobs total", len(all_jobs))
        return all_jobs


register_adapter("morningstar", MorningstarScraper)
