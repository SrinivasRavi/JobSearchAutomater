"""Deutsche Bank scraper adapter — Beesite JSON API."""
import logging
from urllib.parse import urlparse, parse_qs

import httpx

from src.scrapers.base import BaseScraper, RawJob
from src.scrapers.registry import register_adapter

logger = logging.getLogger("jobsearch.scrapers.deutsche_bank")

API_BASE = "https://api-deutschebank.beesite.de/search/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _parse_jobs_from_response(data: dict) -> list[RawJob]:
    """Parse Deutsche Bank Beesite API response into RawJob list."""
    jobs = []
    result = data.get("SearchResult", {})
    for item in result.get("SearchResultItems", []):
        descriptor = item.get("MatchedObjectDescriptor", item)
        title = descriptor.get("PositionTitle", "")
        position_id = descriptor.get("PositionID", "")
        uri = descriptor.get("PositionURI", "")
        if uri and not uri.startswith("http"):
            uri = f"https://careers.db.com{uri}"
        locations = descriptor.get("PositionLocation", [])
        location_str = ", ".join(
            f"{loc.get('CityName', loc.get('City', ''))} {loc.get('CountryName', loc.get('Country', ''))}".strip()
            for loc in locations
        )

        jobs.append(RawJob(
            company_name="Deutsche Bank",
            job_title=title,
            job_description=f"{title} - {location_str}" if location_str else title,
            job_link=uri,
            location=location_str,
        ))
    return jobs


class DeutscheBankScraper(BaseScraper):
    """Scrapes Deutsche Bank via Beesite JSON API."""

    def source_name(self) -> str:
        return "deutsche_bank"

    def fetch_jobs(self) -> list[RawJob]:
        parsed = urlparse(self.url)
        fragment_params = parse_qs(parsed.fragment.split("?")[-1]) if "?" in parsed.fragment else {}
        params = {k: v[0] if isinstance(v, list) else v for k, v in fragment_params.items()}

        api_params = {
            "country": params.get("country", "81"),
            "profession": params.get("profession", "1330"),
            "category": params.get("category", "1328"),
            "rows": "200",
        }

        logger.info("Fetching Deutsche Bank API: %s", api_params)
        response = httpx.get(API_BASE, params=api_params,
                             headers=HEADERS, timeout=30.0)
        response.raise_for_status()
        data = response.json()

        jobs = _parse_jobs_from_response(data)
        logger.info("Deutsche Bank scraper found %d jobs", len(jobs))
        return jobs


register_adapter("deutsche_bank", DeutscheBankScraper)
