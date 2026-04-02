# Progress Log

## How to use
Append a new entry for each meaningful task or coding session.

Each entry should capture:
- what was attempted,
- what changed,
- what decisions were made,
- what blockers appeared,
- what should happen next.

Keep entries brief and factual.

---

## Template

### Date
YYYY-MM-DD

### Task
Short task name

### Goal
What this task was supposed to achieve

### Files changed
- path/to/file1
- path/to/file2

### What changed
- concrete change 1
- concrete change 2
- concrete change 3

### Decisions made
- decision 1
- decision 2

### Validation
- test run / manual check / not run
- result

### Blockers
- blocker or `None`

### Next recommended task
- next small task

---

## Entries

### Date
2026-04-01

### Task
Project docs initialization

### Goal
Create the minimal working documentation set so Claude Code can work iteratively without large-context prompts.

### Files changed
- CLAUDE.md
- docs/current-sprint.md
- docs/todo.md
- docs/progress.md

### What changed
- Added root-level Claude Code instructions.
- Added current sprint scope for v1 seeded career-page scraper.
- Added prioritized todo list with small task slices.
- Added progress log template for future sessions.

### Decisions made
- Keep `CLAUDE.md` concise so it does not waste context.
- Treat `docs/current-sprint.md` as the source of truth for active implementation scope.
- Keep future milestones out of active coding unless explicitly requested.

### Validation
- Documentation only.
- Manual review required.

### Blockers
- None

### Next recommended task
- Create initial repo structure and define the v1 Job model plus status enum.

---

### Date
2026-04-01

### Task
v0 — Foundations: schema, models, persistence, base scraper, utilities

### Goal
Define the minimum stable contracts (data models, persistence layer, dedupe, base scraper interface, URL cleaning) so v1 can be built on solid ground.

### Files changed
- `src/models/enums.py` — ApplicationStatus, SourceType, FilterReason enums
- `src/models/job.py` — Job dataclass with to_dict() and dedupe_key property
- `src/persistence/database.py` — SQLite connection, schema creation (jobs, scrape_runs, scrape_errors tables with indexes)
- `src/persistence/repository.py` — JobRepository with insert (dedupe via unique constraint), exists, get_by_id, count, list_jobs, update_status, scrape run/error logging
- `src/scrapers/base.py` — BaseScraper ABC, RawJob dataclass, ScraperResult dataclass
- `src/utils/url_cleaner.py` — clean_job_link with optional keep_params for source-specific overrides
- `src/utils/logging_config.py` — Standard logging setup
- `config/sources.yaml` — All 20 curated company URLs registered
- `docs/dreaming-doc.md` — Added section 21: Architecture decisions
- `tests/unit/test_models.py` — 7 tests for enums and Job model
- `tests/unit/test_url_cleaner.py` — 11 tests for URL cleaning
- `tests/unit/test_repository.py` — 15 tests for persistence, dedupe, schema constraints, run/error logging
- `tests/unit/test_base_scraper.py` — 5 tests for scraper contract
- `requirements.txt` — Python dependencies
- `.gitignore` — Standard Python ignores

### What changed
- Full v0 foundation implemented with TDD (44 tests, all passing)
- SQLite chosen as datastore with WAL mode, foreign keys, and indexes on clean_job_link (unique), company_name, application_status, scraped_timestamp
- BaseScraper supports both HTML and API-based sources via abstract fetch_jobs()
- clean_job_link supports keep_params for sources that encode job ID in query params
- Architecture decisions documented in dreaming-doc.md section 21

### Decisions made
- Python 3.11+ with SQLite (local-first, zero-config, sufficient for 100K+ rows)
- Layered scraping: HTTP+HTML → API interception → Browser automation → External APIs
- Repository pattern isolates all SQL; swapping to PostgreSQL is a single-module change
- Source registry is YAML-based config (config/sources.yaml)
- v2 Chrome extension will communicate via local HTTP API (FastAPI on localhost)

### Validation
- 44 unit tests, all passing (0.03s)
- Covers: models, enums, URL cleaning, persistence insert/dedupe/query, schema constraints, base scraper contract

### Blockers
- None

### Next recommended task
- Implement the first source adapter (pick the simplest career page from the curated list)

---

### Date
2026-04-01

### Task
v1 first source: Amazon scraper, orchestrator, CSV export, CLI

### Goal
Build the first working end-to-end scrape pipeline: source adapter → orchestrator → persist → dedupe → CSV export.

### Files changed
- `src/scrapers/amazon.py` — Amazon Jobs adapter using JSON search API (pagination, URL construction)
- `src/scrapers/orchestrator.py` — ScrapeOrchestrator: runs scrapers, normalizes, dedupes, persists, logs runs/errors
- `src/scrapers/registry.py` — Config-driven scraper registry with adapter auto-registration
- `src/utils/csv_export.py` — CSV export of persisted jobs
- `src/cli.py` — CLI entrypoint with scrape, export, stats commands
- `tests/unit/test_amazon_scraper.py` — 7 tests for Amazon adapter (parsing, pagination, error handling)
- `tests/unit/test_orchestrator.py` — 8 tests for orchestrator (dedupe, error isolation, run logging)
- `tests/unit/test_csv_export.py` — 5 tests for CSV export

### What changed
- Amazon adapter uses `search.json` API endpoint (Layer 2 — API interception)
- Orchestrator isolates per-source failures, logs runs to scrape_runs table
- Registry auto-imports adapters and matches them to sources.yaml entries
- CLI supports `--source` filter, `--json` output, CSV export to file or stdout
- Live integration test passed: 2 Amazon Mumbai jobs scraped, persisted, deduplicated on re-run, exported to CSV

### Decisions made
- Amazon chosen as first source because it has a native JSON API (easiest, most reliable)
- Research found: Barclays & Citi use TalentBrew (server-side HTML, BeautifulSoup parseable), BofA needs Playwright (hardest)
- Scraper registry uses module-level `register_adapter()` calls for self-registration

### Validation
- 64 unit tests, all passing (0.07s)
- Live test: Amazon API returned 2 jobs for Mumbai software engineer search
- Dedupe verified: second run inserted 0, skipped 2

### Blockers
- None

### Next recommended task
- Add Barclays and Citi adapters (same TalentBrew platform, server-side HTML)

---

### Date
2026-04-02

### Task
v1 adapters batch 2: Barclays, Citi, Nomura, Deutsche Bank, Visa, MSCI

### Goal
Build adapters for 6 more curated sources. Bring total to 7 working adapters covering 3 scraping approaches: JSON API, HTML parsing, and Algolia search.

### Files changed
- `src/scrapers/barclays.py` — TalentBrew HTML parser with pagination
- `src/scrapers/citi.py` — TalentBrew HTML parser with pagination
- `src/scrapers/nomura.py` — SAP SuccessFactors HTML table parser
- `src/scrapers/deutsche_bank.py` — Beesite REST API (country filter broken)
- `src/scrapers/visa.py` — SmartRecruiters public API
- `src/scrapers/msci.py` — Algolia search API with public credentials
- `src/scrapers/registry.py` — Added all 7 adapters to auto-import
- Tests for all 6 new adapters (28 new tests)

### What changed
- 7 adapters total across 4 scraping layers: JSON API (Amazon, Deutsche Bank, Visa), HTML parsing (Barclays, Citi, Nomura), Algolia (MSCI)
- Research completed on all 20 curated sources — classified by difficulty
- Live tested: Amazon=2, Barclays=36, Citi=96, Nomura=42, Deutsche Bank=10 (wrong country), Visa=17, MSCI=5
- 92 unit tests + 1 integration test, all passing

### Decisions made
- 11 of 20 sources need Playwright (HARD): Goldman, JPMorgan, Oracle, Morgan Stanley, Microsoft, BofA, S&P, Nasdaq, BNP Paribas, Morningstar, UBS
- Google is MODERATE (embedded JS data, no browser needed)
- Deutsche Bank API ignores country filter — needs further investigation
- Will add Playwright-based adapters in a later batch

### Validation
- 92 unit tests, all passing (0.16s)
- Live tests passed for 6 of 7 new adapters (Deutsche Bank works but returns wrong country)

### Blockers
- Deutsche Bank Beesite API does not respect country filter — returns only German jobs
- 11 sources need Playwright which is not yet integrated

### Next recommended task
- Investigate Deutsche Bank country filtering
- Add Google adapter (embedded JS data parsing)
- Or: set up Playwright for the 11 HARD sources

---

### Date
2026-04-02

### Task
v1 profile support, CLI enhancements, pagination fixes, live validation

### Goal
Add multi-profile support (Mumbai + Pune), enhance CLI with query/runs/profiles commands, fix pagination bugs, and validate the full pipeline end-to-end.

### Files changed
- `config/sources.yaml` — Restructured to profile-based format with mumbai and pune profiles
- `src/scrapers/registry.py` — Profile-aware source loading, `--profile` support
- `src/cli.py` — Added query, runs, profiles commands; --profile flag on scrape
- `src/persistence/repository.py` — Added count_by_company, count_by_source, get_recent_runs methods
- `src/scrapers/citi.py` — Fixed infinite pagination loop (same-URL guard)
- `src/scrapers/barclays.py` — Fixed infinite pagination loop (same-URL guard)

### What changed
- sources.yaml restructured from flat list to profile-based config (mumbai, pune)
- Registry updated to load sources by profile name, with enabled/disabled flag support
- CLI scrape command accepts `--profile` (default: mumbai)
- New CLI commands: `query` (browse jobs with filters), `runs` (scrape history), `profiles` (list profiles)
- Repository gained aggregate queries: count_by_company, count_by_source, get_recent_runs
- Fixed Citi and Barclays pagination: last page's "next" link pointed to itself, causing infinite loop. Added `if next_url == current_url: break` guard
- Deutsche Bank disabled in config (`enabled: false`) due to broken country filter

### Decisions made
- Profile-based config allows location variants without duplicating adapter code
- Cross-profile dedupe works naturally: both profiles share the same database and clean_job_link unique constraint
- Deutsche Bank punted to v1.1 until API country filtering is resolved
- Hard sources (11 Playwright-dependent) explicitly deferred per user request

### Validation
- Mumbai scrape: 151 discovered, 141 inserted, 10 skipped, 0 errors (6 sources)
- Pune scrape: 151 discovered, 49 inserted, 102 skipped, 0 errors (cross-profile dedupe working)
- Total in database: 190 jobs across 6 sources
- All CLI commands (stats, query, runs, profiles) working correctly
- 92 unit tests still passing

### Blockers
- None

### Next recommended task
- User to validate full workflow and data quality
- After satisfaction: set up Playwright for hard sources, or move to v1.1 planning

---

### Date
2026-04-02

### Task
v1.1 — 8 new adapters: HTTP APIs + Playwright scrapers, location field, run-commands doc

### Goal
Expand scraper coverage from 7 to 14 working sources by adding 4 HTTP API adapters and 4 Playwright browser-based adapters. Add `location` field to jobs. Create user-facing run commands reference.

### Files changed
- `src/scrapers/playwright_base.py` — NEW: PlaywrightScraper base class with browser lifecycle
- `src/scrapers/morningstar.py` — NEW: Phenom People platform (phApp.ddo JS data extraction)
- `src/scrapers/jpmorgan.py` — NEW: Oracle HCM REST API adapter
- `src/scrapers/nasdaq.py` — NEW: Workday CXS REST API adapter
- `src/scrapers/oracle_careers.py` — NEW: Oracle HCM REST API adapter
- `src/scrapers/goldman_sachs.py` — NEW: Playwright adapter for higher.gs.com
- `src/scrapers/google.py` — NEW: Playwright adapter for Google Careers SPA
- `src/scrapers/bofa.py` — NEW: Playwright adapter for Bank of America (Adobe AEM)
- `src/scrapers/microsoft.py` — NEW: Playwright adapter for Microsoft (Eightfold)
- `src/scrapers/base.py` — Added `location` field to RawJob
- `src/models/job.py` — Added `location` field to Job
- `src/persistence/database.py` — Schema migration for location column
- `src/persistence/repository.py` — Insert/read location field
- `src/scrapers/orchestrator.py` — Pass location through normalization
- `src/scrapers/registry.py` — Added 8 new adapter imports
- `src/utils/csv_export.py` — Added location to CSV columns
- `src/cli.py` — Show location in query output
- `config/sources.yaml` — Enabled 8 new sources, disabled 5 blocked sources
- `requirements.txt` — Added playwright dependency
- `docs/run-commands.md` — NEW: user-facing command reference
- All 7 existing adapters updated to populate location field
- 3 new test files: test_jpmorgan_scraper.py (7 tests), test_nasdaq_scraper.py (7 tests), test_oracle_scraper.py (5 tests)
- Existing tests updated for location field

### What changed
- **4 HTTP API adapters**: Morningstar (Phenom phApp.ddo → json.raw_decode), JPMorgan (Oracle HCM API), Nasdaq (Workday CXS POST API), Oracle (Oracle HCM API)
- **4 Playwright adapters**: Goldman Sachs (higher.gs.com), Google (li.lLd3Je), BofA (job-result cards), Microsoft (Eightfold positions)
- **PlaywrightScraper base**: manages browser lifecycle (launch → context → page → cleanup), headless Chromium
- **Location field**: added to RawJob, Job, DB schema (with migration), CSV export, CLI
- **Goldman Sachs URL fix**: Mumbai filter returned 0 results, changed to LOCATION=India (273 jobs)
- **Morningstar JSON fix**: regex-based extraction failed on large phApp.ddo objects, switched to json.JSONDecoder.raw_decode

### Decisions made
- Reclassified 4 sources from Playwright to HTTP-only after discovering their APIs (Morningstar phApp.ddo, JPMorgan/Oracle HCM REST, Nasdaq Workday CXS)
- 5 sources permanently disabled: Morgan Stanley (reCAPTCHA), UBS (login+CAPTCHA), BNP Paribas (WAF 403), S&P Global (hCaptcha), Deutsche Bank (wrong country)
- Goldman Sachs uses India-wide filter since no Mumbai-specific jobs exist
- PlaywrightScraper handles timeout gracefully (returns empty list, no crash)

### Validation
- 125 unit tests, all passing (0.18s)
- Live test results: JPMorgan=500, Goldman Sachs=273, Oracle=126, Morningstar=54, Citi=49, Amazon=49, Nomura=42, Barclays=26, Nasdaq=25, Visa=17, Google=16, Microsoft=14, MSCI=7, BofA=4
- Total in database: 1,201 jobs across 14 active sources
- Dedupe working across runs (skipped counts on re-runs)

### Blockers
- None

### Next recommended task
- Live test Pune profile with new sources
- Begin v2 planning (auto-applier, form-filler)