# Current Sprint

## Sprint name
v1 — Seeded career-page scraper

## Goal
Build the smallest useful version of JobSearchAutomater by scraping a curated list of career-page URLs that already contain filters, then persisting discovered jobs into a dataset with minimal required fields and intra-scraper dedupe.

## Why this sprint exists
This sprint is meant to be the easiest small win.
The URLs are already curated and filtered by the user, so the system can focus on:
- scraping,
- normalization,
- persistence,
- dedupe,
- logging.

No dynamic source discovery is required in this sprint.

## In scope
- Scrape from a given list of known career-page job listing URLs.
- Assume the supplied URLs are already filtered correctly.
- Persist jobs with at least:
  - company_name
  - job_title
  - job_description
  - job_link
  - posted_timestamp if available
  - scraped_timestamp
  - application_status defaulting to `NOT_APPLIED`
- Use a clean job link as dedupe key.
- Ensure the same scraper instance never persists the same job twice.
- Record scrape failures without crashing the whole run.
- Produce a dataset that can be viewed directly by the user.
- Export to CSV if useful.
- Keep code ready for later source adapter expansion.

## Out of scope
- Auto-discovery of company career pages.
- Auto-application.
- LinkedIn post scraping.
- Human-in-the-loop application flows.
- Multi-profile orchestration.
- Global cross-workflow dedupe.
- Scoring.
- Referral automation.
- Tracker UI beyond direct dataset access.
- Cover letters.
- Fancy analytics.

## Inputs
The user provides curated company listing URLs.
These URLs should be treated as the current source inventory for v1.

## Source list 
- Bank of America
https://careers.bankofamerica.com/en-us/job-search?ref=search&search=jobsByLocation&rows=10&start=0&keywords=software+engineer&sort=newest&searchstring=Mumbai%2C+India
- JPMorganChase
https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs?keyword=Software+Engineer&location=Mumbai%2C+Maharashtra%2C+India&locationId=300000081151360&locationLevel=city&mode=location&radius=25&radiusUnit=MI&sortBy=POSTING_DATES_DESC
- Morgan Stanley
https://morganstanley.eightfold.ai/careers?source=mscom&query=Software+Engineer&start=0&pid=549795890684&sort_by=relevance&filter_businessarea=technology&filter_employmenttype=full+time&filter_city=Mumbai
- Nomura
https://careers.nomura.com/Nomura/go/Career-Opportunities-India/9050900/?q=&q2=&alertId=&title=software+engineer&facility=&location=mumbai#searchresults
- Google
https://www.google.com/about/careers/applications/jobs/results/?location=Mumbai%2C%20India&employment_type=FULL_TIME&skills=engineer
- Goldman Sachs
https://higher.gs.com/results?JOB_FUNCTION=Software%20Engineering&LOCATION=Mumbai&page=1&sort=RELEVANCE
- Barclays
https://search.jobs.barclays/search-jobs?k=software+engineer&l=Mumbai%2C+Maharashtra&orgIds=13015
- Deutsche Bank
https://careers.db.com/professionals/search-roles/#/professional/results/?divisionProf=undefined&searchType=profession&category=1328&profession=1330&country=81
- UBS
https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5012&PageType=searchResults&SearchType=linkquery&LinkID=15231#keyWordSearch=software&locationSearch=Mumbai
- Citi
https://jobs.citi.com/category/software-engineer-jobs/287/8644128/1
- BNP Paribas
https://group.bnpparibas/en/careers/all-job-offers?q=software%20engineer&city=379%7C2998%7C3000
- S&P Global
https://careers.spglobal.com/jobs?keywords=software%20engineer&location=mumbai&stretch=10&stretchUnit=MILES&sortBy=relevance&page=1
- MSCI
https://careers.msci.com/job-search?production__mscicare2201__sort-rank%5Bquery%5D=Developer&production__mscicare2201__sort-rank%5BrefinementList%5D%5Btown_city_country%5D%5B0%5D=Mumbai%20%7C%20India
- Morningstar
https://careers.morningstar.com/us/en/c/product-development-jobs
- Nasdaq
https://nasdaq.wd1.myworkdayjobs.com/Global_External_Site?q=software%20engineer&Location_Country=c4f78be1a8f14da0ab49ce1162348a5e&locations=84ab8350a70e10019c78e4295b9b0000&locations=b638d7611d08100143bd56aa78670000&timeType=c5d5bf172e3c019da4ea33754c384e00
- Oracle
https://careers.oracle.com/en/sites/jobsearch/jobs?keyword=software+developer&location=MUMBAI%2C+MAHARASHTRA%2C+India&locationId=300001842985413&locationLevel=city&mode=location&radius=25&radiusUnit=MI
- Microsoft
https://apply.careers.microsoft.com/careers?query=Software+Development&start=0&location=India%2C+Maharashtra%2C+Mumbai&pid=1970393556842859&sort_by=relevance&filter_distance=160&filter_include_remote=1
- Amazon
https://www.amazon.jobs/en/search?offset=0&result_limit=10&sort=relevant&category%5B%5D=software-development&job_type%5B%5D=Full-Time&distanceType=Mi&radius=24km&latitude=18.94018&longitude=72.83484&loc_group_id=&loc_query=Mumbai%2C%20Maharashtra%2C%20India&base_query=software&city=Mumbai&country=IND&region=Maharashtra&county=Mumbai&query_options=&
- Visa
https://www.visa.co.uk/en_gb/jobs/?categories=Software%20Development%2FEngineering&cities=Mumbai

## Expected behavior
For each source URL:
1. Fetch or load the listing page.
2. Extract all jobs visible/reachable from that listing flow.
3. Normalize the result into the internal Job data object.
4. Clean the job link.
5. Skip persisting if the same scraper has already persisted that clean link.
6. Persist otherwise.
7. Log success/failure counts for the run.

## Minimum job model for this sprint
- company_name
- job_title
- job_description
- job_link
- clean_job_link
- posted_timestamp (nullable)
- scraped_timestamp
- application_status

## Current dedupe rule
Use the clean job link as the dedupe key.
For now, “clean” means removing query params and fragments unless a source requires a stable identifying parameter that would otherwise collapse different jobs incorrectly.

If a source proves this rule unsafe, do not silently invent a new global rule. Document the issue in `docs/progress.md` and propose a source-specific exception.

## Current statuses needed
Only the minimum statuses needed for v1:
- NOT_APPLIED
- APPLY_FAILED
- APPLIED
- HEARD_BACK
- REJECTED

If internal implementation needs extra transient states, keep them internal and minimal.

## Non-functional expectations
- Keep implementation simple.
- Prefer deterministic parsing over LLM extraction.
- Keep source-specific logic isolated.
- Fail one source without failing the whole run.
- Make reruns safe.
- Local-first execution.

## Acceptance criteria
A task in this sprint is done when:
- it only implements v1 scope,
- it preserves the minimum job model,
- it uses intra-scraper dedupe,
- it logs failures clearly,
- it does not introduce speculative future-milestone complexity,
- it updates `docs/progress.md`.

## Task sizing rule
Any implementation task should usually fit one of these shapes:
- schema only,
- one utility only,
- one source adapter only,
- one persistence feature only,
- one logging feature only,
- one test file only.

If a task touches too many areas, split it first.

## Default prompt style for this sprint
When working on a task:
- restate the task,
- list files to be changed,
- give a short plan first
- subsequent prompts you may start executing without asking for permissions.
