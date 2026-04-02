"""Scrape orchestrator — runs scrapers, normalizes, dedupes, persists."""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.models.job import Job
from src.models.enums import ApplicationStatus, SourceType
from src.persistence.repository import JobRepository
from src.scrapers.base import BaseScraper, RawJob
from src.utils.url_cleaner import clean_job_link

logger = logging.getLogger("jobsearch.orchestrator")


@dataclass
class RunSummary:
    total_discovered: int = 0
    total_inserted: int = 0
    total_skipped: int = 0
    total_errors: int = 0
    source_results: list[dict] = field(default_factory=list)


class ScrapeOrchestrator:
    def __init__(self, repo: JobRepository):
        self._repo = repo

    def run(self, scrapers: list[BaseScraper]) -> RunSummary:
        summary = RunSummary()

        for scraper in scrapers:
            result = scraper.scrape()
            discovered = len(result.jobs)
            inserted = 0
            skipped = 0

            for raw_job in result.jobs:
                job = self._normalize(raw_job, result.source_name)
                if self._repo.exists(job.clean_job_link):
                    skipped += 1
                    continue
                job_id = self._repo.insert(job)
                if job_id is not None:
                    inserted += 1
                else:
                    skipped += 1

            errors_count = len(result.errors)
            for error_msg in result.errors:
                logger.error("Scraper %s error: %s", result.source_name, error_msg)

            self._repo.log_scrape_run(
                source_name=result.source_name,
                started_at=result.started_at,
                ended_at=result.ended_at,
                jobs_discovered=discovered,
                jobs_inserted=inserted,
                jobs_skipped=skipped,
                errors_count=errors_count,
            )

            if errors_count > 0:
                run_cursor = self._repo._db.connection.execute(
                    "SELECT MAX(run_id) FROM scrape_runs"
                )
                run_id = run_cursor.fetchone()[0]
                for error_msg in result.errors:
                    self._repo.log_scrape_error(
                        run_id=run_id,
                        source_name=result.source_name,
                        error_type="SCRAPER_ERROR",
                        message=error_msg,
                    )

            summary.total_discovered += discovered
            summary.total_inserted += inserted
            summary.total_skipped += skipped
            summary.total_errors += errors_count
            summary.source_results.append({
                "source": result.source_name,
                "discovered": discovered,
                "inserted": inserted,
                "skipped": skipped,
                "errors": errors_count,
            })

        return summary

    def _normalize(self, raw: RawJob, source_name: str) -> Job:
        cleaned = clean_job_link(raw.job_link)
        return Job(
            company_name=raw.company_name,
            job_title=raw.job_title,
            job_description=raw.job_description,
            job_link=raw.job_link,
            clean_job_link=cleaned,
            posted_timestamp=raw.posted_timestamp,
            scraped_timestamp=datetime.now(timezone.utc),
            application_status=ApplicationStatus.NOT_APPLIED,
            source_type=SourceType.CAREER_PAGE,
            source_name=source_name,
            location=raw.location,
        )
