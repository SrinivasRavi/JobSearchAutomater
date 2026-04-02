# Current Sprint

## Sprint name
v2 — Human-Approved Apply Assistant

## Status
Planning complete. See `docs/v2-sprint.md` for full architecture decisions, task breakdown, and implementation notes.

## Quick summary
Move from job discovery to job application. Playwright in headed mode fills forms using a UserProfile config. Human confirms each submission in terminal. Chrome extension built independently and integrated later.

## Task order (Python-first)
1. UserProfile model + multi-YAML loader
2. Application persistence (DB tables + repository)
3. BaseFormFiller interface + filler registry
4. Apply orchestrator (CLI → Playwright → filler → confirm)
5. Oracle HCM form filler (highest value: 625 jobs)
6. Workday form filler (Nasdaq + widely used platform)
7. ATS URL detection + apply-link resolution
8. Apply-stats CLI + run-commands update

Tasks 1-3 are independent and can be built in parallel.
Task 4 depends on 1-3.
Tasks 5-8 depend on 4.

## Key architecture decisions (already resolved)
- Playwright headed mode for CLI batch flow
- Chrome extension built independently, integrated later (see Appendix in v2-sprint.md)
- Multiple UserProfiles via separate YAML files in `config/profiles/`
- Per-ATS form filler adapters (same pattern as scrapers)
- Separate applications + application_attempts tables
- ATS account management deferred to v2.1
- Human-in-the-loop is mandatory (no autopilot)

## For full details
Read `docs/v2-sprint.md` — it has exact interfaces, schemas, selectors, and implementation notes. The Appendix has a standalone Chrome extension build spec.
