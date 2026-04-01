"""SQLite database connection and schema management."""
import sqlite3
import os

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    job_description TEXT NOT NULL,
    job_link TEXT NOT NULL,
    clean_job_link TEXT NOT NULL UNIQUE,
    posted_timestamp TEXT,
    scraped_timestamp TEXT NOT NULL,
    application_status TEXT NOT NULL DEFAULT 'NOT_APPLIED',
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_name);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(application_status);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped ON jobs(scraped_timestamp);

CREATE TABLE IF NOT EXISTS scrape_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    jobs_discovered INTEGER NOT NULL DEFAULT 0,
    jobs_inserted INTEGER NOT NULL DEFAULT 0,
    jobs_skipped INTEGER NOT NULL DEFAULT 0,
    errors_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS scrape_errors (
    error_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    source_name TEXT NOT NULL,
    error_type TEXT NOT NULL,
    message TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES scrape_runs(run_id)
);
"""


class Database:
    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._connection: sqlite3.Connection | None = None

    def initialize(self):
        if self._db_path != ":memory:":
            os.makedirs(os.path.dirname(self._db_path) or ".", exist_ok=True)
        self._connection = sqlite3.connect(self._db_path)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(_SCHEMA_SQL)

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._connection

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None
