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

## Now
- [ ] Implement one source adapter only, for a single company URL.
- [ ] Persist discovered jobs from the first source.
- [ ] Add CSV export of persisted jobs.
- [ ] Add run summary output: discovered, inserted, skipped_duplicate, failed.

## After first source works
- [ ] Add second source adapter.
- [ ] Add third source adapter.
- [ ] Refactor shared extraction helpers only if repeated patterns are proven.
- [ ] Add source-by-source enable/disable switch.
- [ ] Add retry behavior for transient source failures.
- [ ] Add per-source timeout handling.

## Later in v1
- [ ] Add remaining curated company listing sources.
- [ ] Improve normalization consistency across sources.
- [ ] Review whether clean link dedupe is safe for every source.
- [ ] Add optional local dataset viewer or simple query script if needed.
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