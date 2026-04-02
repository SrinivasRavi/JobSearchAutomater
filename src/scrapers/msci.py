"""MSCI scraper adapter — Algolia search API with public credentials."""
import logging
from urllib.parse import urlparse, parse_qs

import httpx

from src.scrapers.base import BaseScraper, RawJob
from src.scrapers.registry import register_adapter

logger = logging.getLogger("jobsearch.scrapers.msci")

ALGOLIA_APP_ID = "RVMOB42DFH"
ALGOLIA_API_KEY = "629e647c6a9a8b542fb1022001313a7e"
ALGOLIA_INDEX = "production__mscicare2201__sort-rank"
ALGOLIA_URL = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"
CAREERS_BASE = "https://careers.msci.com"
MAX_PAGES = 10
PAGE_SIZE = 50


def _parse_jobs_from_response(data: dict) -> list[RawJob]:
    """Parse Algolia search response into RawJob list."""
    jobs = []
    for hit in data.get("hits", []):
        object_id = hit.get("objectID", "")
        title = hit.get("title", "")
        city = hit.get("town_city", "")
        country = hit.get("country", "")
        location = f"{city}, {country}" if city and country else city or country
        description = hit.get("description", title)
        job_link = f"{CAREERS_BASE}/job/{object_id}"

        jobs.append(RawJob(
            company_name="MSCI",
            job_title=title,
            job_description=description[:500] if description else title,
            job_link=job_link,
        ))
    return jobs


class MsciScraper(BaseScraper):
    """Scrapes MSCI careers via Algolia public API."""

    def source_name(self) -> str:
        return "msci"

    def fetch_jobs(self) -> list[RawJob]:
        parsed = urlparse(self.url)
        params = parse_qs(parsed.query)
        query = ""
        facet_filters = []

        for key, values in params.items():
            if "query" in key:
                query = values[0]
            elif "town_city_country" in key:
                facet_filters.append([f"town_city_country:{values[0]}"])

        all_jobs: list[RawJob] = []
        headers = {
            "X-Algolia-Application-Id": ALGOLIA_APP_ID,
            "X-Algolia-API-Key": ALGOLIA_API_KEY,
            "Content-Type": "application/json",
        }

        for page in range(MAX_PAGES):
            body = {
                "query": query,
                "hitsPerPage": PAGE_SIZE,
                "page": page,
            }
            if facet_filters:
                body["facetFilters"] = facet_filters

            logger.info("Fetching MSCI Algolia page %d", page + 1)
            response = httpx.post(ALGOLIA_URL, json=body,
                                  headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            page_jobs = _parse_jobs_from_response(data)
            all_jobs.extend(page_jobs)

            nb_pages = data.get("nbPages", 1)
            if page + 1 >= nb_pages or len(page_jobs) == 0:
                break

        logger.info("MSCI scraper found %d jobs total", len(all_jobs))
        return all_jobs


register_adapter("msci", MsciScraper)
