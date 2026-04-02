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
    from src.scrapers.registry import get_scrapers

    profile = getattr(args, "profile", None)
    scrapers = get_scrapers(profile=profile, source_filter=args.source)
    if not scrapers:
        print(f"No scrapers found for profile='{profile or 'mumbai'}'"
              f"{f', source={args.source}' if args.source else ''}")
        print("Check config/sources.yaml and ensure adapters are registered.")
        return

    print(f"Running {len(scrapers)} scraper(s) for profile '{profile or 'mumbai'}'...")
    print()

    orch = ScrapeOrchestrator(repo)
    summary = orch.run(scrapers)

    print(f"\n--- Scrape Summary ---")
    print(f"Profile:          {profile or 'mumbai'}")
    print(f"Total discovered: {summary.total_discovered}")
    print(f"Total inserted:   {summary.total_inserted}")
    print(f"Total skipped:    {summary.total_skipped}")
    print(f"Total errors:     {summary.total_errors}")
    print()
    for sr in summary.source_results:
        status = "OK" if sr["errors"] == 0 else "ERR"
        print(f"  [{status}] {sr['source']:20s} "
              f"discovered={sr['discovered']:3d} "
              f"inserted={sr['inserted']:3d} "
              f"skipped={sr['skipped']:3d} "
              f"errors={sr['errors']}")

    if args.json:
        print()
        print(json.dumps({
            "profile": profile or "mumbai",
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
    print(f"\n--- Job Statistics ---")
    print(f"Total jobs in database: {total}")
    print()

    if total == 0:
        print("No jobs yet. Run 'scrape' first.")
        return

    print("By status:")
    for status in ApplicationStatus:
        c = repo.count(status=status)
        if c > 0:
            print(f"  {status.value:15s} {c:5d}")

    print()
    print("By company:")
    companies = repo.count_by_company()
    for company, count in sorted(companies.items(), key=lambda x: -x[1]):
        print(f"  {company:25s} {count:5d}")

    print()
    print("By source:")
    sources = repo.count_by_source()
    for source, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {source:25s} {count:5d}")


def cmd_query(args, repo):
    """Query and browse jobs in the database."""
    filters = {}
    if args.company:
        filters["company_name"] = args.company
    if args.status:
        from src.models.enums import ApplicationStatus
        filters["status"] = ApplicationStatus(args.status)

    jobs = repo.list_jobs(
        limit=args.limit,
        company_name=filters.get("company_name"),
        status=filters.get("status"),
    )

    if not jobs:
        print("No jobs found matching your filters.")
        return

    print(f"\nShowing {len(jobs)} job(s):\n")
    for job in jobs:
        print(f"  [{job.job_id:4d}] {job.company_name:20s} | {job.job_title[:50]:50s} | {job.application_status.value}")
        print(f"         {job.clean_job_link}")
        print()


def cmd_runs(args, repo):
    """Show recent scrape run history."""
    runs = repo.get_recent_runs(limit=args.limit)
    if not runs:
        print("No scrape runs recorded yet.")
        return

    print(f"\n--- Recent Scrape Runs ---\n")
    for run in runs:
        print(f"  Run #{run['run_id']:3d} | {run['source_name']:15s} | "
              f"{run['started_at'][:19]} | "
              f"discovered={run['jobs_discovered']:3d} "
              f"inserted={run['jobs_inserted']:3d} "
              f"skipped={run['jobs_skipped']:3d} "
              f"errors={run['errors_count']}")


def cmd_profiles(args, repo):
    """List available profiles."""
    from src.scrapers.registry import list_profiles, _load_config
    config = _load_config()
    profiles = config.get("profiles", {})

    print("\n--- Available Profiles ---\n")
    for name, profile in profiles.items():
        label = profile.get("label", name)
        sources = profile.get("sources", [])
        enabled = [s for s in sources if s.get("enabled", True) is not False]
        print(f"  {name:15s} | {label}")
        print(f"  {'':15s} | {len(enabled)} enabled sources, {len(sources) - len(enabled)} disabled")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="JobSearchAutomater — job discovery and tracking CLI"
    )
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to SQLite database")
    subparsers = parser.add_subparsers(dest="command")

    # scrape
    p_scrape = subparsers.add_parser("scrape", help="Run scrapers to discover jobs")
    p_scrape.add_argument("--profile", "-p", default="mumbai",
                          help="Profile to scrape (default: mumbai)")
    p_scrape.add_argument("--source", "-s", help="Run only this source adapter")
    p_scrape.add_argument("--json", action="store_true", help="Output summary as JSON")

    # export
    p_export = subparsers.add_parser("export", help="Export jobs to CSV")
    p_export.add_argument("--output", "-o", help="Output file path (default: stdout)")

    # stats
    subparsers.add_parser("stats", help="Show job statistics")

    # query
    p_query = subparsers.add_parser("query", help="Browse jobs in the database")
    p_query.add_argument("--company", "-c", help="Filter by company name")
    p_query.add_argument("--status", help="Filter by status (NOT_APPLIED, APPLIED, etc.)")
    p_query.add_argument("--limit", "-n", type=int, default=20, help="Number of results")

    # runs
    p_runs = subparsers.add_parser("runs", help="Show recent scrape run history")
    p_runs.add_argument("--limit", "-n", type=int, default=20, help="Number of runs to show")

    # profiles
    subparsers.add_parser("profiles", help="List available scraping profiles")

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
        "query": cmd_query,
        "runs": cmd_runs,
        "profiles": cmd_profiles,
    }
    commands[args.command](args, repo)
    db.close()


if __name__ == "__main__":
    main()
