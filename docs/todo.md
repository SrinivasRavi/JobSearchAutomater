# Todo

## Done (v0)
- [x] Create initial repo structure for scraper, persistence, and shared utilities.
- [x] Define the v1 Job model in code.
- [x] Define application status enum with minimum statuses for v1.
- [x] Create persistence schema for jobs.
- [x] Add unique constraint or equivalent logic for intra-scraper dedupe using clean job link.
- [x] Implement `clean_job_link` utility.
- [x] Create scrape run logging model/table/file.
- [x] Create scrape error logging model/table/file.
- [x] Add tests for clean link dedupe.
- [x] Add tests for “same scraper must never persist same job twice”.
- [x] Add source configuration file for curated URLs.

## Done (v1 first source)
- [x] Implement one source adapter only, for a single company URL. (Amazon — JSON API)
- [x] Persist discovered jobs from the first source.
- [x] Add CSV export of persisted jobs.
- [x] Add run summary output: discovered, inserted, skipped_duplicate, failed.
- [x] Add scrape orchestrator with per-source error isolation.
- [x] Add CLI entrypoint (scrape, export, stats commands).
- [x] Add scraper registry with config-driven source loading.
- [x] Live integration test passed: Amazon scraper → persist → dedupe → CSV export.

## Done (v1 adapters batch 2)
- [x] Barclays adapter (TalentBrew HTML, pagination) — 36 jobs live
- [x] Citi adapter (TalentBrew HTML, pagination) — 96 jobs live
- [x] Nomura adapter (SAP SuccessFactors HTML table) — 42 jobs live
- [x] Deutsche Bank adapter (Beesite JSON API) — works but country filter broken (API ignores param)
- [x] Visa adapter (SmartRecruiters JSON API) — 17 jobs live
- [x] MSCI adapter (Algolia JSON API) — 5 jobs live

## Done (v1 profile support & CLI enhancements)
- [x] Multi-profile support (mumbai, pune) in sources.yaml and registry
- [x] CLI `--profile` flag for scrape command
- [x] CLI `query` command (browse jobs with --company, --status, --limit filters)
- [x] CLI `runs` command (scrape history)
- [x] CLI `profiles` command (list available profiles)
- [x] Repository aggregate queries (count_by_company, count_by_source, get_recent_runs)
- [x] Fixed Citi pagination infinite loop (same-URL guard)
- [x] Fixed Barclays pagination infinite loop (same-URL guard)
- [x] Source-by-source enable/disable switch (enabled: false in sources.yaml)
- [x] Live validation: 190 jobs across 6 sources, 0 errors, cross-profile dedupe working

## Now
- [ ] Investigate Deutsche Bank country filtering (Beesite API ignores country param) — punted to v1.1
- [ ] Add retry behavior for transient source failures.
- [ ] Add per-source timeout handling.

## Remaining sources — by difficulty
### EASY/MODERATE (no browser needed)
- [ ] Google — embedded JS data in AF_initDataCallback, parseable
### HARD (need Playwright/headless browser)
- [ ] Goldman Sachs — Next.js SPA, Apollo GraphQL, needs session
- [ ] JPMorgan — Oracle HCM SPA, needs session
- [ ] Oracle — Oracle HCM SPA, needs session
- [ ] Morgan Stanley — Eightfold SPA, CSRF-gated API
- [ ] Microsoft — Eightfold SPA, CSRF-gated API
- [ ] Bank of America — Adobe AEM, fully client-rendered
- [ ] S&P Global — Jibe SPA, API-driven
- [ ] Nasdaq — Workday SPA, needs session
- [ ] BNP Paribas — Akamai WAF blocks non-browser requests
- [ ] Morningstar — Phenom People, client-rendered widgets
- [ ] UBS — IBM BrassRing, session-gated AJAX

## Later in v1
- [ ] Improve normalization consistency across sources.
- [ ] Review whether clean link dedupe is safe for every source.
- [ ] Add documentation for how to run one source vs all sources.
- [ ] Add smoke test for full scrape run.

## Explicitly not now
- [ ] Auto-apply.
- [ ] Browser extension.
- [ ] Account creation on ATS sites.
- [ ] LinkedIn post scraping.
- [ ] Multi-profile workflows.
- [ ] Cross-workflow dedupe.
- [ ] Scoring.
- [ ] Referral outreach.
- [ ] Cover letter generation.
- [ ] Analytics dashboard.

## Task template
Use this format when adding a new task:

### Task
Short title

### Why
Why this is needed now

### Acceptance criteria
- measurable condition 1
- measurable condition 2
- measurable condition 3

### Out of scope
- not doing X
- not doing Y

### Notes
Anything source-specific or risky