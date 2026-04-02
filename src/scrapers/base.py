"""Base scraper interface and shared types."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class RawJob:
    """Raw job data as extracted from a source, before normalization."""
    company_name: str
    job_title: str
    job_description: str
    job_link: str
    location: str = ""
    posted_timestamp: Optional[datetime] = None


@dataclass
class ScraperResult:
    """Result of a single scraper run."""
    source_name: str
    jobs: list[RawJob]
    errors: list[str]
    started_at: datetime
    ended_at: datetime


class BaseScraper(ABC):
    """Abstract base class for all source adapters.

    Subclasses implement source_name() and fetch_jobs().
    The scrape() method handles timing and error capture.
    """

    def __init__(self, url: str):
        self.url = url

    @abstractmethod
    def source_name(self) -> str:
        """Return a stable identifier for this source (e.g. 'bank_of_america')."""
        ...

    @abstractmethod
    def fetch_jobs(self) -> list[RawJob]:
        """Fetch raw jobs from the source. May raise on failure."""
        ...

    def scrape(self) -> ScraperResult:
        """Execute the scraper with timing and error handling."""
        started_at = datetime.now(timezone.utc)
        jobs: list[RawJob] = []
        errors: list[str] = []

        try:
            jobs = self.fetch_jobs()
        except Exception as e:
            errors.append(f"{type(e).__name__}: {e}")

        ended_at = datetime.now(timezone.utc)
        return ScraperResult(
            source_name=self.source_name(),
            jobs=jobs,
            errors=errors,
            started_at=started_at,
            ended_at=ended_at,
        )
