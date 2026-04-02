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