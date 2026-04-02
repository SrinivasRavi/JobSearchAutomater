"""Job and Application repositories — persistence layer."""
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from src.models.job import Job
from src.models.enums import ApplicationStatus, SourceType
from src.persistence.database import Database


class JobRepository:
    def __init__(self, db: Database):
        self._db = db

    def insert(self, job: Job) -> Optional[int]:
        """Insert a job. Returns job_id on success, None if duplicate clean_job_link."""
        conn = self._db.connection
        try:
            cursor = conn.execute(
                "INSERT INTO jobs (company_name, job_title, job_description, job_link, "
                "clean_job_link, posted_timestamp, scraped_timestamp, application_status, "
                "source_type, source_name, location) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    job.company_name,
                    job.job_title,
                    job.job_description,
                    job.job_link,
                    job.clean_job_link,
                    job.posted_timestamp.isoformat() if job.posted_timestamp else None,
                    job.scraped_timestamp.isoformat(),
                    job.application_status.value,
                    job.source_type.value,
                    job.source_name,
                    job.location,
                ),
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def exists(self, clean_job_link: str) -> bool:
        cursor = self._db.connection.execute(
            "SELECT 1 FROM jobs WHERE clean_job_link = ? LIMIT 1",
            (clean_job_link,),
        )
        return cursor.fetchone() is not None

    def get_by_id(self, job_id: int) -> Optional[Job]:
        cursor = self._db.connection.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def count(self, status: Optional[ApplicationStatus] = None) -> int:
        if status:
            cursor = self._db.connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE application_status = ?",
                (status.value,),
            )
        else:
            cursor = self._db.connection.execute("SELECT COUNT(*) FROM jobs")
        return cursor.fetchone()[0]

    def list_jobs(
        self,
        limit: int = 100,
        offset: int = 0,
        company_name: Optional[str] = None,
        status: Optional[ApplicationStatus] = None,
    ) -> list[Job]:
        query = "SELECT * FROM jobs WHERE 1=1"
        params: list = []
        if company_name:
            query += " AND company_name = ?"
            params.append(company_name)
        if status:
            query += " AND application_status = ?"
            params.append(status.value)
        query += " ORDER BY scraped_timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = self._db.connection.execute(query, params)
        return [self._row_to_job(row) for row in cursor.fetchall()]

    def update_status(self, job_id: int, status: ApplicationStatus) -> None:
        self._db.connection.execute(
            "UPDATE jobs SET application_status = ? WHERE job_id = ?",
            (status.value, job_id),
        )
        self._db.connection.commit()

    def log_scrape_run(
        self,
        source_name: str,
        started_at: datetime,
        ended_at: datetime,
        jobs_discovered: int,
        jobs_inserted: int,
        jobs_skipped: int,
        errors_count: int,
    ) -> int:
        cursor = self._db.connection.execute(
            "INSERT INTO scrape_runs (source_name, started_at, ended_at, "
            "jobs_discovered, jobs_inserted, jobs_skipped, errors_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                source_name,
                started_at.isoformat(),
                ended_at.isoformat(),
                jobs_discovered,
                jobs_inserted,
                jobs_skipped,
                errors_count,
            ),
        )
        self._db.connection.commit()
        return cursor.lastrowid

    def log_scrape_error(
        self,
        run_id: int,
        source_name: str,
        error_type: str,
        message: str,
    ) -> None:
        self._db.connection.execute(
            "INSERT INTO scrape_errors (run_id, source_name, error_type, message) "
            "VALUES (?, ?, ?, ?)",
            (run_id, source_name, error_type, message),
        )
        self._db.connection.commit()

    def count_by_company(self) -> dict[str, int]:
        cursor = self._db.connection.execute(
            "SELECT company_name, COUNT(*) as cnt FROM jobs GROUP BY company_name ORDER BY cnt DESC"
        )
        return {row[0]: row[1] for row in cursor.fetchall()}

    def count_by_source(self) -> dict[str, int]:
        cursor = self._db.connection.execute(
            "SELECT source_name, COUNT(*) as cnt FROM jobs GROUP BY source_name ORDER BY cnt DESC"
        )
        return {row[0]: row[1] for row in cursor.fetchall()}

    def get_recent_runs(self, limit: int = 20) -> list[dict]:
        cursor = self._db.connection.execute(
            "SELECT * FROM scrape_runs ORDER BY run_id DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        posted = row["posted_timestamp"]
        scraped = row["scraped_timestamp"]
        return Job(
            job_id=row["job_id"],
            company_name=row["company_name"],
            job_title=row["job_title"],
            job_description=row["job_description"],
            job_link=row["job_link"],
            clean_job_link=row["clean_job_link"],
            posted_timestamp=datetime.fromisoformat(posted) if posted else None,
            scraped_timestamp=datetime.fromisoformat(scraped),
            application_status=ApplicationStatus(row["application_status"]),
            source_type=SourceType(row["source_type"]),
            source_name=row["source_name"],
            location=row["location"],
        )


class ApplicationRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create_application(
        self,
        job_id: Optional[int],
        profile_name: str,
        job_url: str,
        job_title: str = "",
        company_name: str = "",
        ats_platform: str = "",
        apply_method: str = "cli",
    ) -> int:
        cursor = self._conn.execute(
            "INSERT INTO applications (job_id, profile_name, job_url, job_title, "
            "company_name, ats_platform, apply_method) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job_id, profile_name, job_url, job_title, company_name, ats_platform, apply_method),
        )
        self._conn.commit()
        return cursor.lastrowid

    def update_status(
        self,
        app_id: int,
        status: str,
        failure_reason: str = "",
        notes: str = "",
    ) -> None:
        applied_ts = datetime.now(timezone.utc).isoformat() if status == "SUBMITTED" else None
        self._conn.execute(
            "UPDATE applications SET status = ?, failure_reason = ?, notes = ?, "
            "applied_timestamp = COALESCE(?, applied_timestamp) WHERE id = ?",
            (status, failure_reason, notes, applied_ts, app_id),
        )
        self._conn.commit()

    def log_attempt(
        self,
        app_id: int,
        result: str,
        error_message: str = "",
        screenshot_path: str = "",
    ) -> None:
        self._conn.execute(
            "INSERT INTO application_attempts (application_id, result, error_message, screenshot_path) "
            "VALUES (?, ?, ?, ?)",
            (app_id, result, error_message, screenshot_path),
        )
        self._conn.commit()

    def get_attempts(self, app_id: int) -> list[dict]:
        cursor = self._conn.execute(
            "SELECT * FROM application_attempts WHERE application_id = ? ORDER BY id",
            (app_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_by_job_id(self, job_id: int) -> Optional[dict]:
        cursor = self._conn.execute(
            "SELECT * FROM applications WHERE job_id = ? ORDER BY id DESC LIMIT 1",
            (job_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_pending_jobs(self, limit: int = 10) -> list[dict]:
        """Return NOT_APPLIED jobs that have no application record yet."""
        cursor = self._conn.execute(
            "SELECT j.* FROM jobs j "
            "LEFT JOIN applications a ON a.job_id = j.job_id "
            "WHERE j.application_status = 'NOT_APPLIED' AND a.id IS NULL "
            "ORDER BY j.scraped_timestamp DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> dict:
        by_status = {
            row[0]: row[1]
            for row in self._conn.execute(
                "SELECT status, COUNT(*) FROM applications GROUP BY status"
            ).fetchall()
        }
        by_profile = {
            row[0]: row[1]
            for row in self._conn.execute(
                "SELECT profile_name, COUNT(*) FROM applications GROUP BY profile_name"
            ).fetchall()
        }
        by_method = {
            row[0]: row[1]
            for row in self._conn.execute(
                "SELECT apply_method, COUNT(*) FROM applications GROUP BY apply_method"
            ).fetchall()
        }
        return {"by_status": by_status, "by_profile": by_profile, "by_method": by_method}

    def list_applications(
        self,
        status: Optional[str] = None,
        profile: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        query = "SELECT * FROM applications WHERE 1=1"
        params: list = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if profile:
            query += " AND profile_name = ?"
            params.append(profile)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        cursor = self._conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
