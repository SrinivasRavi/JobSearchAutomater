"""Amazon Jobs scraper adapter — uses the JSON search API."""
import logging
from urllib.parse import urlparse, parse_qs, urlencode

import httpx

from src.scrapers.base import BaseScraper, RawJob
from src.scrapers.registry import register_adapter

logger = logging.getLogger("jobsearch.scrapers.amazon")

BASE_URL = "https://www.amazon.jobs"
MAX_PAGES = 20
DEFAULT_PAGE_SIZE = 10


def _parse_jobs_from_response(data: dict) -> list[RawJob]:
    """Parse Amazon API JSON response into RawJob list."""
    jobs = []
    for item in data.get("jobs", []):
        job_path = item.get("job_path", "")
        if job_path and not job_path.startswith("http"):
            job_link = f"{BASE_URL}{job_path}"
        else:
            job_link = item.get("url_next_step", job_path)

        location = item.get("location", "")

        jobs.append(RawJob(
            company_name=item.get("company_name", "Amazon"),
            job_title=item.get("title", ""),
            job_description=item.get("description_short", ""),
            job_link=job_link,
            location=location,
        ))
    return jobs


class AmazonScraper(BaseScraper):
    """Scrapes Amazon Jobs via their JSON search API."""

    def source_name(self) -> str:
        return "amazon"

    def fetch_jobs(self) -> list[RawJob]:
        parsed = urlparse(self.url)
        params = parse_qs(parsed.query, keep_blank_values=False)
        flat_params = {k: v[0] if isinstance(v, list) else v for k, v in params.items()}

        page_size = int(flat_params.get("result_limit", DEFAULT_PAGE_SIZE))
        offset = int(flat_params.get("offset", 0))

        all_jobs: list[RawJob] = []

        for page in range(MAX_PAGES):
            flat_params["offset"] = str(offset)
            flat_params["result_limit"] = str(page_size)

            api_url = f"{BASE_URL}/en/search.json?{urlencode(flat_params)}"
            logger.info("Fetching Amazon page %d: offset=%s", page + 1, offset)

            response = httpx.get(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json",
            }, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            page_jobs = _parse_jobs_from_response(data)
            all_jobs.extend(page_jobs)

            total_hits = data.get("hits", 0)
            offset += page_size

            if offset >= total_hits or len(page_jobs) == 0:
                break

        logger.info("Amazon scraper found %d jobs total", len(all_jobs))
        return all_jobs


register_adapter("amazon", AmazonScraper)
