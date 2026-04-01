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