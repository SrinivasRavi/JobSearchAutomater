"""CSV export for job data."""
import csv
from typing import IO

from src.persistence.repository import JobRepository

COLUMNS = [
    "job_id",
    "company_name",
    "job_title",
    "location",
    "job_link",
    "clean_job_link",
    "posted_timestamp",
    "scraped_timestamp",
    "application_status",
    "source_type",
    "source_name",
]


def export_jobs_csv(repo: JobRepository, output: IO[str], limit: int = 10000) -> int:
    """Export jobs to CSV. Returns number of rows written."""
    writer = csv.DictWriter(output, fieldnames=COLUMNS)
    writer.writeheader()

    jobs = repo.list_jobs(limit=limit)
    for job in jobs:
        d = job.to_dict()
        row = {col: d.get(col, "") for col in COLUMNS}
        writer.writerow(row)

    return len(jobs)
