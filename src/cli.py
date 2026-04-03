"""CLI entrypoint for the job search scraper and apply assistant."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

from src.persistence.database import Database
from src.persistence.repository import ApplicationRepository, JobRepository
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
        loc = f" | {job.location}" if job.location else ""
        print(f"  [{job.job_id:4d}] {job.company_name:20s} | {job.job_title[:50]:50s} | {job.application_status.value}")
        print(f"         {job.location or 'N/A'}")
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
    """List available scraping profiles."""
    from src.scrapers.registry import list_profiles, _load_config
    config = _load_config()
    profiles = config.get("profiles", {})

    print("\n--- Available Scraping Profiles ---\n")
    for name, profile in profiles.items():
        label = profile.get("label", name)
        sources = profile.get("sources", [])
        enabled = [s for s in sources if s.get("enabled", True) is not False]
        print(f"  {name:15s} | {label}")
        print(f"  {'':15s} | {len(enabled)} enabled sources, {len(sources) - len(enabled)} disabled")
        print()


def cmd_list_profiles(args, repo):
    """List available UserProfile YAML files for applying."""
    from src.models.user_profile import list_profiles as list_user_profiles
    profiles = list_user_profiles()
    if not profiles:
        print("No profiles found in config/profiles/. Copy config/profiles/example.yaml to get started.")
        return
    print("\n--- Available User Profiles ---\n")
    for name, summary in profiles:
        print(f"  {name:20s} | {summary}")
    print()


def cmd_apply(args, db):
    """Apply to a job using Playwright."""
    from src.models.user_profile import load_profile, list_profiles as list_user_profiles
    from src.applier.orchestrator import ApplyOrchestrator

    # Load profile
    if args.profile:
        profile_name = args.profile
    else:
        profiles = list_user_profiles()
        if not profiles:
            print("No profiles found. Create config/profiles/your_profile.yaml first.")
            return
        profile_name = profiles[0][0]
        print(f"Using profile: {profile_name}")

    try:
        profile = load_profile(profile_name)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    app_repo = ApplicationRepository(db.connection)
    job_repo = JobRepository(db)
    orch = ApplyOrchestrator(db.connection, profile)

    if args.job_id:
        job = job_repo.get_by_id(args.job_id)
        if not job:
            print(f"Job {args.job_id} not found.")
            return
        result = orch.apply_to_url(
            job_url=job.clean_job_link,
            job_id=job.job_id,
            job_title=job.job_title,
            company_name=job.company_name,
        )
        print(f"Result: {result.status}" + (f" ({result.failure_reason})" if result.failure_reason else ""))

    elif args.next:
        pending = app_repo.get_pending_jobs(limit=args.limit or 1)
        if not pending:
            print("No pending jobs in the apply queue.")
            return
        for row in pending:
            print(f"\nApplying to: {row['job_title']} @ {row['company_name']}")
            result = orch.apply_to_url(
                job_url=row["clean_job_link"],
                job_id=row["job_id"],
                job_title=row["job_title"],
                company_name=row["company_name"],
            )
            print(f"Result: {result.status}" + (f" ({result.failure_reason})" if result.failure_reason else ""))
    else:
        print("Specify --job-id or --next")


def cmd_apply_queue(args, db):
    """Show the apply queue (NOT_APPLIED jobs without an application record)."""
    app_repo = ApplicationRepository(db.connection)
    pending = app_repo.get_pending_jobs(limit=args.limit)
    if not pending:
        print("Apply queue is empty.")
        return
    print(f"\n--- Apply Queue ({len(pending)} jobs) ---\n")
    for row in pending:
        print(f"  [{row['job_id']:4d}] {row['company_name']:20s} | {row['job_title'][:50]}")
        print(f"         {row['clean_job_link']}")
        print()


def cmd_apply_stats(args, db):
    """Show application statistics."""
    app_repo = ApplicationRepository(db.connection)
    stats = app_repo.get_stats()

    print("\n--- Application Statistics ---\n")
    print("By status:")
    for status, count in sorted(stats["by_status"].items()):
        print(f"  {status:15s} {count:5d}")

    print("\nBy profile:")
    for profile, count in sorted(stats["by_profile"].items()):
        print(f"  {profile:20s} {count:5d}")

    print("\nBy method:")
    for method, count in sorted(stats["by_method"].items()):
        print(f"  {method:10s} {count:5d}")


def cmd_applications(args, db):
    """List past application records."""
    app_repo = ApplicationRepository(db.connection)
    apps = app_repo.list_applications(
        status=args.status or None,
        profile=args.profile or None,
        limit=args.limit,
    )
    if not apps:
        print("No applications found.")
        return
    print(f"\n--- Applications ({len(apps)}) ---\n")
    for a in apps:
        status_str = a["status"]
        reason = f" ({a['failure_reason']})" if a.get("failure_reason") else ""
        print(f"  [{a['id']:4d}] {a['company_name']:20s} | {a['job_title'][:40]:40s} | {status_str}{reason}")
        print(f"         profile={a['profile_name']} | {a['job_url'][:60]}")
        print()


def cmd_mark_applied(args, db):
    """Mark a job as manually applied."""
    app_repo = ApplicationRepository(db.connection)
    job_repo = JobRepository(db)

    job = job_repo.get_by_id(args.job_id)
    if not job:
        print(f"Job {args.job_id} not found.")
        return

    app_id = app_repo.create_application(
        job_id=job.job_id,
        profile_name=args.profile or "manual",
        job_url=job.clean_job_link,
        job_title=job.job_title,
        company_name=job.company_name,
        apply_method="manual",
    )
    app_repo.update_status(app_id, "SUBMITTED", notes="Marked as applied manually")
    print(f"Marked job {args.job_id} ({job.company_name} — {job.job_title}) as applied.")


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

    # profiles (scraping profiles)
    subparsers.add_parser("profiles", help="List available scraping profiles")

    # list-profiles (user YAML profiles for applying)
    subparsers.add_parser("list-profiles", help="List available user profiles for applying")

    # apply
    p_apply = subparsers.add_parser("apply", help="Apply to a job using Playwright")
    p_apply.add_argument("--job-id", type=int, help="Apply to this specific job ID")
    p_apply.add_argument("--next", action="store_true", help="Apply to next pending job")
    p_apply.add_argument("--limit", "-n", type=int, default=1, help="Number of jobs (with --next)")
    p_apply.add_argument("--profile", "-p", help="Profile name to use (default: first available)")

    # apply-queue
    p_queue = subparsers.add_parser("apply-queue", help="Show jobs in the apply queue")
    p_queue.add_argument("--limit", "-n", type=int, default=20)

    # apply-stats
    subparsers.add_parser("apply-stats", help="Show application statistics")

    # applications
    p_apps = subparsers.add_parser("applications", help="List past application records")
    p_apps.add_argument("--status", help="Filter by status (PENDING, SUBMITTED, FAILED, SKIPPED)")
    p_apps.add_argument("--profile", "-p", help="Filter by profile name")
    p_apps.add_argument("--limit", "-n", type=int, default=50)

    # mark-applied
    p_mark = subparsers.add_parser("mark-applied", help="Mark a job as manually applied")
    p_mark.add_argument("--job-id", type=int, required=True)
    p_mark.add_argument("--profile", "-p", help="Profile name used (default: 'manual')")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    db = Database(args.db)
    db.initialize()
    repo = JobRepository(db)

    # Commands that receive db directly (need ApplicationRepository too)
    db_commands = {"apply", "apply-queue", "apply-stats", "applications", "mark-applied"}

    if args.command in db_commands:
        db_command_map = {
            "apply": cmd_apply,
            "apply-queue": cmd_apply_queue,
            "apply-stats": cmd_apply_stats,
            "applications": cmd_applications,
            "mark-applied": cmd_mark_applied,
        }
        db_command_map[args.command](args, db)
    else:
        commands = {
            "scrape": cmd_scrape,
            "export": cmd_export,
            "stats": cmd_stats,
            "query": cmd_query,
            "runs": cmd_runs,
            "profiles": cmd_profiles,
            "list-profiles": cmd_list_profiles,
        }
        commands[args.command](args, repo)

    db.close()


if __name__ == "__main__":
    main()
