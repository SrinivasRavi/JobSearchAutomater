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
- [x] Add tests for "same scraper must never persist same job twice".
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
- [x] Deutsche Bank adapter (Beesite JSON API) — works but country filter broken, disabled
- [x] Visa adapter (SmartRecruiters JSON API) — 17 jobs live
- [x] MSCI adapter (Algolia JSON API) — 5 jobs live

## Done (v1 profile support & CLI enhancements)
- [x] Multi-profile support (mumbai, pune) in sources.yaml and registry
- [x] CLI `--profile` flag for scrape command
- [x] CLI `query` command (browse jobs with --company, --status, --limit filters)
- [x] CLI `runs` command (scrape history)
- [x] CLI `profiles` command (list available profiles)
- [x] Repository aggregate queries (count_by_company, count_by_source, get_recent_runs)
- [x] Fixed Citi/Barclays pagination infinite loop (same-URL guard)
- [x] Source-by-source enable/disable switch (enabled: false in sources.yaml)

## Done (v1.1 — expanded coverage)
- [x] PlaywrightScraper base class with browser lifecycle management
- [x] Morningstar adapter (Phenom phApp.ddo, json.raw_decode) — 54 jobs
- [x] JPMorgan adapter (Oracle HCM REST API) — 500 jobs
- [x] Nasdaq adapter (Workday CXS REST API) — 25 jobs
- [x] Oracle adapter (Oracle HCM REST API) — 126 jobs
- [x] Goldman Sachs adapter (Playwright, higher.gs.com) — 273 jobs
- [x] Google adapter (Playwright, li.lLd3Je) — 16 jobs
- [x] Bank of America adapter (Playwright, Adobe AEM) — 4 jobs
- [x] Microsoft adapter (Playwright, Eightfold) — 14 jobs
- [x] Location field added to Job model, DB, all adapters, CLI, CSV
- [x] DB migration for existing databases (ALTER TABLE ADD COLUMN)
- [x] `docs/run-commands.md` user-facing command reference
- [x] 125 unit tests, all passing
- [x] 1,201 total jobs across 14 sources

## v1 — Complete
v1 is done. 14 of 20 curated sources are working. 5 are blocked by anti-bot (reCAPTCHA, hCaptcha, WAF, login-required) and 1 has a broken API filter. These are site limitations, not missing work.

## v2 — See docs/v2-sprint.md

## Explicitly not now
- [ ] LinkedIn post scraping.
- [ ] Cross-workflow dedupe.
- [ ] Scoring / fit ranking.
- [ ] Referral outreach.
- [ ] Cover letter generation.
- [ ] Analytics dashboard.
