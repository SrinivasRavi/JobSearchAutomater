"""CLI entrypoint for the job search scraper."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

from src.persistence.database import Database
from src.persistence.repository import JobRepository
from src.scrapers.orchestrator import ScrapeOrchestrator
from src.utils.csv_export import export_jobs_csv
from src.utils.logging_config import setup_logging

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "jobs.db"
)


def cmd_scrape(args, repo):
    """Run scrapers and persist results."""
    logger = setup_logging()
    # Import adapters here to avoid circular imports and allow per-source selection
    from src.scrapers.registry import get_scrapers

    scrapers = get_scrapers(source_filter=args.source)
    if not scrapers:
        logger.warning("No scrapers found%s", f" for source '{args.source}'" if args.source else "")
        return

    orch = ScrapeOrchestrator(repo)
    summary = orch.run(scrapers)

    print(f"\n--- Scrape Summary ---")
    print(f"Total discovered: {summary.total_discovered}")
    print(f"Total inserted:   {summary.total_inserted}")
    print(f"Total skipped:    {summary.total_skipped}")
    print(f"Total errors:     {summary.total_errors}")
    print()
    for sr in summary.source_results:
        print(f"  [{sr['source']}] discovered={sr['discovered']} "
              f"inserted={sr['inserted']} skipped={sr['skipped']} errors={sr['errors']}")

    if args.json:
        print(json.dumps({
            "total_discovered": summary.total_discovered,
            "total_inserted": summary.total_inserted,
            "total_skipped": summary.total_skipped,
            "total_errors": summary.total_errors,
            "sources": summary.source_results,
        }, indent=2))


def cmd_export(args, repo):
    """Export jobs to CSV."""
    if args.output:
        with open(args.output, "w") as f:
            count = export_jobs_csv(repo, f)
        print(f"Exported {count} jobs to {args.output}")
    else:
        count = export_jobs_csv(repo, sys.stdout)


def cmd_stats(args, repo):
    """Print job statistics."""
    from src.models.enums import ApplicationStatus
    total = repo.count()
    print(f"Total jobs: {total}")
    for status in ApplicationStatus:
        c = repo.count(status=status)
        if c > 0:
            print(f"  {status.value}: {c}")


def main():
    parser = argparse.ArgumentParser(description="JobSearchAutomater CLI")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to SQLite database")
    subparsers = parser.add_subparsers(dest="command")

    p_scrape = subparsers.add_parser("scrape", help="Run scrapers")
    p_scrape.add_argument("--source", help="Run only this source adapter")
    p_scrape.add_argument("--json", action="store_true", help="Output summary as JSON")

    p_export = subparsers.add_parser("export", help="Export jobs to CSV")
    p_export.add_argument("--output", "-o", help="Output file path (default: stdout)")

    p_stats = subparsers.add_parser("stats", help="Show job statistics")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    db = Database(args.db)
    db.initialize()
    repo = JobRepository(db)

    commands = {
        "scrape": cmd_scrape,
        "export": cmd_export,
        "stats": cmd_stats,
    }
    commands[args.command](args, repo)
    db.close()


if __name__ == "__main__":
    main()
