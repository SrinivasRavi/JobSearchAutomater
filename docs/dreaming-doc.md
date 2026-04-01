# JobSearchAutomater — Dreaming Doc

## Document status
- Status: Living document
- Owner: Srini
- Purpose: Product vision, milestone planning, constraints, assumptions, and evolving design decisions
- Audience: Primarily Srini and Claude Code
- Editing rule: This document is expected to change often as the project evolves

---

## 1. Overview

JobSearchAutomater is a private system that automates repetitive clerical job-search work: job discovery, filtering, application submission, tracking, and eventually referral outreach.

The main goal of the product is simple:
- build a capable scraper,
- build a capable form-filler / applier,
- remove manual repetitive work from the job search.

Tracking, analytics, and experimentation are useful side effects, but they are not the main purpose of the product.

This is a live working document. It is not a rigid contract. It exists to capture the current dream, current assumptions, future direction, and evolving implementation thoughts without pretending that every future milestone is already fully understood.

---

## 2. Mission

### Ultimate mission
Eliminate manual job-search labor for the user.

The ideal end-state is:
- the user provides one or more resumes and preferences,
- the system discovers relevant jobs,
- the system applies to them,
- the system tracks outcomes,
- the system later seeks referrals,
- the user’s involvement is reduced to initial setup and monitoring.

### MVP mission
Build a private application that:
- automatically finds jobs,
- filters them,
- records them in a tracker dataset,
- supports human-assisted application submission,
- later evolves into auto-application.

### Success definition
Primary success means:
- the system discovers relevant jobs,
- the system submits applications correctly,
- the system submits them completely,
- the system submits them in a timely manner,
- the submission uses the intended UserProfile.

Secondary success signals include:
- recruiter responses,
- HR calls,
- rejection emails,
- other indications that the pipeline is functioning usefully.

Receiving an offer is out of scope for product success because that depends on interview performance and employer-side decisions rather than only on this system.

Even if the system produces few favorable external outcomes, it can still be valuable by removing manual pain and helping answer the question: does automation materially improve the process?

---

## 3. Product framing

JobSearchAutomater is best understood as a private automation tool for job discovery and job application submission.

Its highest-priority capabilities are:
1. Discovering jobs.
2. Persisting and deduplicating them reliably.
3. Applying using the intended UserProfile.
4. Tracking application outcomes.

Analytics and experimentation are useful supporting capabilities, especially in later versions, but they should not distort the early implementation priorities.

The product should not become a “magic AI job bot.” It should be a disciplined local automation pipeline built with deterministic code where possible.

---

## 4. Goals and non-goals

### Goals
- Automate job discovery from multiple source types.
- Filter jobs to fit a UserProfile’s role and location preferences.
- Record jobs and application events in a persistent dataset.
- Prevent duplicate job records within a scraper instance.
- Build toward capable automated form filling and application submission.
- Keep the system simple, modular, robust, and near-zero cost.
- Support multiple workflows in future versions.

### Non-goals for now
- Guaranteeing interviews or offers.
- Building a public SaaS product.
- Supporting every ATS and every website from day one.
- Building advanced fit scoring before the application pipeline works.
- Building a dedicated polished tracker UI early.
- Solving general resume writing, interview prep, or broad career coaching.

---

## 5. Principles

The system should follow these principles throughout development:

### Simplicity first
Prefer straightforward solutions over clever abstraction, especially in early milestones.

If this document seems to imply too much complexity in later milestones, treat those as north-star ideas, not strict implementation commitments.

### Modularity
Scraper and applier should remain separate modules or services.

Related concerns such as normalization, dedupe, logging, and notifications should also be separable where practical.

### Idempotence
Re-running a scraper or applier should not produce repeated effects within its intended scope.

At minimum:
- the same scraper instance must never persist the same job twice,
- the same workflow must not apply to the same job twice.

### Code over prompting
Prefer deterministic code and APIs over LLM-based inference where possible.

### Cheap infrastructure
Strongly prefer running on the user’s laptop or free/already-paid infrastructure.

This is effectively a $0-budget project.

### Graceful failure
Unknown cases or errors should be logged and isolated rather than crashing the whole system.

### Progressive build
Build the smallest useful working slice first, then expand.

---

## 6. User and UserProfile

### Primary user
The primary user is Srini, a backend-oriented software engineer who wants to remove repetitive manual work from the job search.

A secondary motivation is regret minimization:
even if the system does not produce dramatically better outcomes, building and testing it is valuable because it proves whether this automation path works or not.

### UserProfile concept
A UserProfile is a market-facing applicant configuration.

It represents a truthful but targeted version of the same person for a specific combination of:
- role family,
- geography,
- resume,
- contact channel.

A UserProfile includes:
- resume,
- email,
- phone,
- location,
- other profile details,
- role preferences,
- location preferences,
- optional metadata such as tags or notes.

### Example UserProfiles
- Backend profile: backend/software engineer/software developer roles in Mumbai.
- AI-oriented profile: AI engineer / forward deployed AI engineer / full stack AI engineer roles in Remote.
- Alternate-location backend profile: backend/software engineer roles in Bengaluru.

### Purpose of UserProfiles
The purpose is targeted packaging:
- the right version of the user is shown to the right role,
- different contact information (email) helps infer which profile led to recruiter response,
- multiple valid market-facing lanes can be explored efficiently.

This is not intended to be deceptive. The profiles are truthful and target different real strengths.

---

## 7. Scope by milestone

### v0 — Foundations
Purpose:
Define the minimum stable contracts before too many moving parts are built.

Important note:
The name “v0” is not important. If this milestone name feels too process-heavy, think of it as “minimum decisions before coding v1.”

In scope:
- core data models,
- job/application statuses,
- eligibility rules,
- logging basics,
- minimal repo/service boundaries.

Out of scope:
- advanced scoring,
- referral messaging,
- broad source coverage.

Deliverable:
A small but clear foundation so v1 is not built on unstable assumptions.

### v1 — Seeded career-page scraper
Purpose:
Achieve the easiest small win.

The user provides career-page listing URLs that are already manually filtered. The scraper should initially just scrape what those URLs show.

#### Curated company listing URLs

##### Bank of America
https://careers.bankofamerica.com/en-us/job-search?ref=search&search=jobsByLocation&rows=10&start=0&keywords=software+engineer&sort=newest&searchstring=Mumbai%2C+India

##### JPMorganChase
https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs?keyword=Software+Engineer&location=Mumbai%2C+Maharashtra%2C+India&locationId=300000081151360&locationLevel=city&mode=location&radius=25&radiusUnit=MI&sortBy=POSTING_DATES_DESC

##### Morgan Stanley
https://morganstanley.eightfold.ai/careers?source=mscom&query=Software+Engineer&start=0&pid=549795890684&sort_by=relevance&filter_businessarea=technology&filter_employmenttype=full+time&filter_city=Mumbai

##### Nomura
https://careers.nomura.com/Nomura/go/Career-Opportunities-India/9050900/?q=&q2=&alertId=&title=software+engineer&facility=&location=mumbai#searchresults

##### Google
https://www.google.com/about/careers/applications/jobs/results/?location=Mumbai%2C%20India&employment_type=FULL_TIME&skills=engineer

##### Goldman Sachs
https://higher.gs.com/results?JOB_FUNCTION=Software%20Engineering&LOCATION=Mumbai&page=1&sort=RELEVANCE

##### Barclays
https://search.jobs.barclays/search-jobs?k=software+engineer&l=Mumbai%2C+Maharashtra&orgIds=13015

##### Deutsche Bank
https://careers.db.com/professionals/search-roles/#/professional/results/?divisionProf=undefined&searchType=profession&category=1328&profession=1330&country=81

##### UBS
https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5012&PageType=searchResults&SearchType=linkquery&LinkID=15231#keyWordSearch=software&locationSearch=Mumbai

##### Citi
https://jobs.citi.com/category/software-engineer-jobs/287/8644128/1

##### BNP Paribas
https://group.bnpparibas/en/careers/all-job-offers?q=software%20engineer&city=379%7C2998%7C3000

##### S&P Global
https://careers.spglobal.com/jobs?keywords=software%20engineer&location=mumbai&stretch=10&stretchUnit=MILES&sortBy=relevance&page=1

##### MSCI
https://careers.msci.com/job-search?production__mscicare2201__sort-rank%5Bquery%5D=Developer&production__mscicare2201__sort-rank%5BrefinementList%5D%5Btown_city_country%5D%5B0%5D=Mumbai%20%7C%20India

##### Morningstar
https://careers.morningstar.com/us/en/c/product-development-jobs

##### Nasdaq
https://nasdaq.wd1.myworkdayjobs.com/Global_External_Site?q=software%20engineer&Location_Country=c4f78be1a8f14da0ab49ce1162348a5e&locations=84ab8350a70e10019c78e4295b9b0000&locations=b638d7611d08100143bd56aa78670000&timeType=c5d5bf172e3c019da4ea33754c384e00

##### Oracle
https://careers.oracle.com/en/sites/jobsearch/jobs?keyword=software+developer&location=MUMBAI%2C+MAHARASHTRA%2C+India&locationId=300001842985413&locationLevel=city&mode=location&radius=25&radiusUnit=MI

##### Microsoft
https://apply.careers.microsoft.com/careers?query=Software+Development&start=0&location=India%2C+Maharashtra%2C+Mumbai&pid=1970393556842859&sort_by=relevance&filter_distance=160&filter_include_remote=1

##### Amazon
https://www.amazon.jobs/en/search?offset=0&result_limit=10&sort=relevant&category%5B%5D=software-development&job_type%5B%5D=Full-Time&distanceType=Mi&radius=24km&latitude=18.94018&longitude=72.83484&loc_group_id=&loc_query=Mumbai%2C%20Maharashtra%2C%20India&base_query=software&city=Mumbai&country=IND&region=Maharashtra&county=Mumbai&query_options=&

##### Visa
https://www.visa.co.uk/en_gb/jobs/?categories=Software%20Development%2FEngineering&cities=Mumbai

In scope:
- scrape from the provided list of known career-page listing URLs,
- assume the URLs already contain the needed filters,
- persist jobs with minimum fields:
  - company name,
  - job title,
  - description,
  - job link,
  - posted timestamp if available,
  - scraped timestamp,
  - application status defaulting to NOT_APPLIED,
- prevent duplicate job records within the scraper instance.

Out of scope:
- auto-discovery of company career pages,
- auto-application,
- LinkedIn post scraping,
- multi-profile orchestration.

Deliverable:
A reliable dataset of discovered jobs from curated URLs.

Operational note:
We may likely skip development of v1_alpha, v1_beta, v1_linkedin and may skip directly to v2 after v1. The rest are just scrapers and we can parallely work on them.

### v1_alpha — Vetted-company discovery
Purpose:
Scale discovery across known companies.

In scope:
- start from a list of company names rather than direct listing URLs,
- resolve or maintain the correct India-facing career page for each company,
- filter for role keywords such as software engineer, software developer, backend developer, backend engineer, java developer, and related variants,
- filter for Mumbai-only jobs,
- discard anything already seen in the dataset, including jobs found by v1 or v1_beta.

Out of scope:
- unknown-company broad web search,
- auto-application.

Deliverable:
A larger but still relatively high-trust company-source discovery pipeline.

### v1_beta — Broader source discovery
Purpose:
Scale to less curated and less predictable sources.

In scope:
- scrape job boards and career pages beyond the vetted-company list,
- apply role and location filters similar to v1_alpha,
- record jobs in the same tracker model.

Out of scope:
- treating these results as equally trusted as v1 and v1_alpha.

Operational note:
If and when auto-apply exists, v1 and v1_alpha results should be prioritized ahead of v1_beta.

Deliverable:
A lower-trust discovery stream.

### v1_linkedin — Experimental Linkedin posts based discovery
Purpose:
Test whether LinkedIn posts provide useful job discovery.

In scope:
- discover openings mentioned in recruiter, hiring manager, or employee posts,
- extract enough metadata to track the opportunity and optionally map it to a company role.

Out of scope:
- making LinkedIn the central dependency of the product,
- treating these results as equally trusted as v1 and v1_alpha.

Operational note:
v1_linkedin is just a scraper just like v1 and v1_alpha. It has no relation to auto application capability. That is something we focus for v2.

Deliverable:
An isolated experimental discovery stream.

### v2 — Human-approved apply assistant
Purpose:
Move beyond discovery and realize the first major product value.

In scope:
- everything in v1,
- an apply assistant, likely a Chrome extension or browser automation layer,
- one UserProfile only,
- human-in-the-loop approval before submission,
- if the target platform requires account creation, create the account using the email in the UserProfile and a default password,
- persist enough account detail so the system can log in again in the future.

Proposed human loop:
1. User reviews the tracker dataset.
2. User opens a candidate job.
3. System fills the application.
4. User reviews if needed.
5. User explicitly confirms submit.
6. System records submission result and metadata.

Deliverable:
Assisted auto-apply with explicit human approval.

### v2_autopilot — Zero-click application worker
Purpose:
Remove the human click in safe cases.

In scope:
- everything in v2 except manual final confirmation for jobs that satisfy policy,
- separate worker that applies automatically using one UserProfile,
- retry logic,
- failure logging,
- strict duplicate prevention within the workflow.

Out of scope:
- multi-profile orchestration,
- referral outreach.

Deliverable:
Fully automated apply flow for one profile under guardrails.

### v3 — Multi-profile operation
Purpose:
Support multiple workflows safely.

Workflow =
UserProfile + scraper instance + dataset partition + auto applier

In scope:
- multiple workflows,
- each workflow has its own UserProfile, role preferences, resume, and contact channel,
- separate or logically separate scraper/apply instances per profile,
- a scraper instance must never persist the same job twice,
- a workflow must not apply to the same job twice,
- different workflows may discover, persist, and apply to the same job in early versions.

Important note:
Cross-workflow duplicate applications are acceptable in early multi-profile versions because the system does not yet know which profile is the better match.

Out of scope:
- globally choosing only one winning profile for the same job.
That will come later once scoring exists.

Deliverable:
Multi-profile system with attribution and workflow independence.

#### v3_hil
Human-approved multi-profile mode.

Human effort should be minimized.
A possible UX direction:
- swipe-like approve/reject flow,
- switch between UserProfiles like switching between different accounts,
- each profile has its own feed.

#### v3_autopilot
Autopilot multi-profile mode.

### v4 — Fit scoring
Purpose:
Control which jobs deserve application effort.

v3_hil and v3_autopilot evolve into v4_hil and v4_autopilot.

In scope:
- a scoring system per job/profile pair,
- use score to prioritize, skip, or route jobs to auto-apply versus manual review,
- likely signals:
  - keyword alignment,
  - seniority fit,
  - location fit,
  - must-have skills,
  - historical response data.

Out of scope:
- highly sophisticated LLM-based ranking from day one.

Deliverable:
Basic but useful fit scoring and policy thresholds.

### v5 — Referral automation
Purpose:
Improve response rate for strong-fit jobs.

v4_hil and v4_autopilot evolve into v5_hil and v5_autopilot.

In scope:
- search for employees at target companies, likely on LinkedIn,
- generate or assist with fixed-template referral requests,
- focus only on high-scoring jobs.

Out of scope:
- blind full autopilot messaging without careful review.

Deliverable:
Referral-seeking workflow, likely semi-automated initially.

---

## 8. Functional requirements

### Discovery
The system must:
- ingest jobs from curated career pages, company career pages, broader job boards, and possibly social posts,
- normalize source data into one internal job model,
- store scrape metadata such as source and timestamps,
- support source-specific extraction logic.

### Filtering
The system must:
- filter jobs by role-family keywords,
- filter jobs by location according to UserProfile,
- later support filtering by salary, seniority, and similar constraints where data is available,
- support source-specific logic when data quality varies,
- support simple explainable rules before advanced scoring.

Important note:
Salary and seniority filtering are currently lower priority because many job postings are vague or inconsistent.

### Persistence and dedupe
The system must:
- persist discovered jobs in a tracker dataset,
- allow different scraper workflows to have different partitions in early multi-workflow versions,
- avoid duplicate job records within a scraper instance from the beginning,
- evolve toward broader dedupe across all source types in later versions.

### Application
The system should eventually:
- fill application forms using the selected UserProfile,
- upload the correct resume and contact data,
- create employer-platform accounts when required,
- persist employer-platform login details for future reuse,
- record application attempts, successes, and failures,
- capture screenshots or similar artifacts for debugging where useful,
- support both human-approved and autopilot modes.

### Tracking
The system must:
- track discovered jobs and application outcomes over time,
- later integrate with email connectors for outcome tracking,
- preserve enough metadata to infer which source, profile, and workflow caused an outcome,
- provide a dataset that the user can inspect directly.

A dedicated tracker UI is not important initially.

---

## 9. Non-functional requirements

### Robustness
Failures in one scraper, source, or apply attempt should not take down the entire system.

Errors should be isolated, logged, and retriable where practical.

### Cost
The system should cost the user nothing out of pocket.

Use free credits, local execution, already-paid hardware, and free tiers where possible.

### Repeatability
Where possible, use deterministic code and APIs rather than nondeterministic LLM-driven extraction or actions.

### Simplicity
This is probably the most important principle in the project.

This document may contain details for v3, v4, and v5, but those should be treated as future ideas rather than implementation commitments today.

### Modularity
Scraping, normalization, filtering, application, tracking, and notifications should be separable modules or services.

---

## 10. Core entities

These entities should exist sooner rather than later so the system can grow iteratively without awkward rewrites.

### UserProfile
Represents a targeted applicant configuration.

Suggested fields:
- profile_id
- profile_name
- resume_path or resume_blob_ref
- email
- phone
- location
- preferred_roles
- preferred_locations
- keywords_include
- keywords_exclude
- active_flag
- notes

### Job
Represents a discovered opportunity.

Suggested fields:
- job_id
- source_type
- source_name
- source_job_id if available
- company_name
- title
- location
- job_url
- clean_job_url
- description_raw
- posted_timestamp
- scraped_timestamp
- normalized_role_family
- normalized_location
- dedupe_key
- discovery_status

### Application
Represents an intended or completed submission for a job/profile pair.

Suggested fields:
- application_id
- job_id
- profile_id
- application_status
- applied_timestamp
- submission_channel
- external_application_id if available
- failure_reason
- notes

### ApplicationAttempt
Represents each try, even if it fails.

Suggested fields:
- attempt_id
- application_id
- attempt_timestamp
- mode
- result
- error_code
- screenshot_or_artifact_ref if useful

### ReferralAttempt
Represents outreach for a referral.

Suggested fields:
- referral_attempt_id
- job_id
- profile_id
- target_person
- platform
- message_template_id
- status
- timestamp

### CareerPlatformAccount
Represents a persisted employer-platform login.

Suggested fields:
- account_id
- profile_id
- employer_name
- platform_name
- login_email
- password_ref
- created_timestamp
- last_used_timestamp
- notes

### RunLog / ErrorLog
Represents operational telemetry.

Suggested fields:
- run_id
- component
- source
- started_at
- ended_at
- result
- items_processed
- errors_count
- log_ref

---

## 11. Status model

The system will have these internal states eventually.

- DISCOVERED  
  Initial state before persistence.

- FILTERED_OUT  
  Discarded because of rule mismatch or other reasons.

- ELIGIBLE  
  Passed initial filter checks.

- APPLY_READY  
  Ready to be picked up for application.

- APPLY_ATTEMPTED  
  A worker has picked it up but not finished.

- APPLIED  
  Submission appears successful from our side.

- APPLIED_VERIFIED  
  An email confirmation or user manually confirms the application was actually submitted.

- APPLY_FAILED  
  Apply attempt failed.

- HEARD_BACK  
  Recruiter or HR reached out.

- REJECTED  
  Rejection email or equivalent clear signal.

- CLOSED  
  Self-closed due to being ghosted from the company, for example after 120 to 180 days.

Suggested reason codes for FILTERED_OUT or APPLY_FAILED:
- DUPLICATE_JOB
- DUPLICATE_APPLICATION
- LOCATION_MISMATCH
- ROLE_MISMATCH
- EXPERIENCE_MISMATCH
- SPONSORSHIP_MISMATCH
- FORM_UNSUPPORTED
- CAPTCHA_BLOCKED
- LOGIN_REQUIRED
- UNKNOWN_ERROR

---

## 12. Duplicate prevention

Current working rule:
A clean job link can be the primary dedupe key.

For now:
- remove query params and fragment where safe,
- persist the clean job link,
- use that as the main unique identifier within a scraper instance.

Important nuance:
- a scraper instance must never persist the same job twice,
- the same workflow should not apply to the same job twice,
- different workflows may still discover and apply to the same job in early multi-profile milestones,
- later versions may resolve these conflicts using fit scoring.

If clean-job-link dedupe proves unsafe for a source, a source-specific exception may be introduced later.

---

## 13. Human-in-the-loop design

Current v2 mental model:
- review dataset,
- open jobs,
- let an extension or browser helper fill the form,
- confirm submit.

Clearer v2 human loop:
1. Scraper populates jobs.
2. Rules mark jobs as APPLY_READY or FILTERED_OUT.
3. User reviews APPLY_READY jobs.
4. User clicks prepare application.
5. Browser helper fills the form using the selected UserProfile.
6. User reviews edge cases if needed.
7. User confirms submit.
8. System records result and status transition.

This keeps v2 useful before autopilot is trusted.

---

## 14. Proposed architecture

At a high level, the system should be a modular pipeline rather than one giant script.

Suggested components:
- source adapters,
- normalizer,
- filter/rules engine,
- deduper,
- datastore (I think PostgresSQL or similar relational db on my mac. Mr. Opus, you can tell your suggestions too with reason),
- apply worker,
- tracker dataset or simple data-access path,
- notifier,
- optional analytics layer.

Mr. Opus, Please suggest your recommendations too with reasons.

### Source adapters
Career-page scrapers, job-board scrapers, and social discovery modules.

### Normalizer
Transforms raw source output into canonical Job records.

### Filter/rules engine
Applies keyword, location, and later eligibility logic.

### Deduper
Checks canonical identity and workflow-level submission history.

### Datastore
Stores jobs, profiles, applications, attempts, platform accounts, logs, and outcomes.

### Apply worker
Performs assisted or autopilot form filling and submission.

### Tracker dataset
The user can inspect the dataset directly without needing a polished UI early.

### Notifier
Optional alerts for failures, new jobs, or recruiter responses.

### Analytics layer
Optional, secondary, and only important once the main pipeline works.

The early implementation should remain local-first where possible.

---

## 15. Metrics and experiments

Even though experimentation is not the main product goal, it is still useful to track metrics from the beginning.

### Primary outcome metrics
- recruiter / HR callback rate,
- positive response rate,
- negative response rate,
- time from discovery to response.

### Funnel metrics
- jobs discovered,
- jobs filtered in,
- jobs marked apply-ready,
- applications attempted,
- applications successfully submitted,
- apply failures by reason,
- duplicate jobs prevented,
- duplicate applications prevented.

### Attribution dimensions
Track outcomes by:
- UserProfile,
- resume version,
- source type,
- company,
- role family,
- location,
- human-approved vs autopilot,
- submission timing.

### Example hypotheses
- early application timing improves callback probability,
- a high match score may correlate with better callback probability,
- vetted-company sources may outperform broader lower-trust sources.

These are useful, but they should not distract from building a working scraper and applier first.

---

## 16. Risks and issues

### Source fragility
Scrapers may break because of selector drift, layout changes, or anti-bot mechanisms.

### Platform/policy risk
Social-platform automation, especially LinkedIn, may be risky and fragile.

### Unsupported forms
Some ATS flows may contain custom questions, CAPTCHAs, login requirements, or other obstacles.

In many cases, these should surface as APPLY_FAILED with a meaningful reason code.

### Poor eligibility rules
Loose rules waste applications. Overly strict rules miss good jobs.

### Weak attribution
If results are not mapped back to source, profile, and workflow, future learning becomes difficult.

### State and credential handling
If employer-platform account state is not modeled cleanly, v2 and later apply flows may become brittle.

---

## 17. Assumptions

Current working assumptions:
- the user will provide truthful profile-specific resumes and preferences,
- initial infrastructure will run locally or on free resources,
- not every source or ATS needs support in early milestones,
- the first meaningful product value comes from working discovery plus assisted apply,
- one strong pipeline is more valuable than many brittle ones.

---

## 18. Open questions

These are the biggest unresolved product questions right now.

### What exact fields should define the canonical dedupe key?
Current answer:
Use the clean job link as the primary key for now.

### What are the hard no-apply rules?
Current answer:
Jobs requiring sponsorship or work authorization that do not fit the target profile should be filtered out using SPONSORSHIP_MISMATCH where applicable.

### What should the tracker UI look like first?
Current answer:
No dedicated tracker UI for now.
Maintain the dataset consistently and let the user inspect it directly.

### Which sources are allowed in v1?
Current answer:
Use the curated company listing URLs listed in the v1 section.

### How should unsupported application forms be handled in v2?
Current answer:
The goal is to make v2 broadly robust.
If the system still fails, it should surface APPLY_FAILED with a clear error code.
This is treated as an implementation gap, not a reason to redefine the goal.

### What is the smallest acceptable success threshold for MVP?
Current answer:
Primary success is successful submission, not callback rate.
Callbacks are useful secondary outcomes, not the definition of system success.

### Should v2 support cover letters?
Current answer:
No.
Cover letters are out of scope for MVP.

### What metadata identifies which UserProfile caused a recruiter response?
Current answer:
Different UserProfiles will use different email addresses.
The contacted email strongly suggests which profile produced the outcome.

### At what point should autopilot be allowed to submit without human confirmation?
Current answer:
This decision remains with the user and should not be overengineered right now.

### Should referral outreach begin as draft generation before sending automation?
Current answer:
Maybe, but this is not important right now.

---

## 19. Recommended implementation order

To stay aligned with the simplicity-first principle, implement in this order:

1. Define schema, statuses, and dedupe rules.
2. Build the v1 seeded career-page scraper with persistent storage.
3. Add normalization, filtering, and discard-if-seen behavior.
4. Use the dataset directly rather than building a tracker UI.
5. Add assisted apply for one profile in v2.
6. Expand source coverage only after data model and apply logging are stable.
7. Only later add autopilot, multi-profile workflows, scoring, and referrals.

The main idea:
do not chase broad coverage before the basic loop works.

---

## 20. Current stance

The product should be built first as a local, deterministic automation pipeline.

Highest-leverage near-term interpretation:
- build a trustworthy discovery backbone,
- persist jobs cleanly,
- dedupe within a scraper instance,
- add assisted apply for one profile,
- only then expand into autopilot, multi-profile orchestration, scoring, and referrals.

This document is expected to change as implementation teaches us what really matters.

---

## 21. Architecture decisions (decided 2026-04-01)

### Language: Python 3.11+
Mature scraping ecosystem (requests, httpx, BeautifulSoup, Playwright). Zero compilation overhead. Easy to integrate with LangChain, n8n, MCP servers, and Apify APIs.

### Datastore: SQLite
Local-first, zero-config, single-file database. Handles 100K+ rows with proper indexing in milliseconds. Concurrent writes are not a concern for a single-user tool. All DB access is behind a repository layer so swapping to PostgreSQL later is a single-module change.

Indexes from day one: `clean_job_link` (unique), `company_name`, `application_status`, `scraped_timestamp`.

### Scraping: Layered approach
- **Layer 1 — HTTP + HTML parsing** (requests/httpx + BeautifulSoup): For sites that serve HTML directly.
- **Layer 2 — API interception** (httpx): Many career sites are SPAs with JSON APIs behind them. Call the API directly.
- **Layer 3 — Browser automation** (Playwright): Only when JavaScript rendering is unavoidable and no API exists.
- **Layer 4 — External API sources** (Apify, etc.): Third-party scraper APIs that return JSON.

Each source adapter declares which layer it uses. One adapter failure does not crash the run.

### Source adapter pattern
Each source is an isolated module implementing a `BaseScraper` interface. Supports both HTML-based and API-based sources. Config-driven source registry (YAML) maps company names to URLs and adapter classes.

### Scheduling: CLI + launchd
The scraper is a CLI tool triggered by macOS launchd (or cron). No long-running daemon. `caffeinate` can prevent idle sleep during runs. A second always-on Mac (locked, plugged in, sleep disabled) is the simplest "server."

### Integration surface for v2+ and external tools
- **Python API:** `JobRepository` is importable by any Python module (LangChain agents, MCP tools, scoring modules).
- **CLI with JSON output:** Callable from n8n "Execute Command" nodes, cron, or shell scripts.
- **Local HTTP API (v2):** A thin FastAPI layer on top of the same repository. The Chrome extension and any external tool become API clients.

### v2 Chrome extension interface
The extension communicates with a local HTTP API:
- `GET /api/next-job?status=APPLY_READY` → returns job + UserProfile fields
- `POST /api/application` → reports submission result
- The backend owns all state; the extension is a stateless form-filler.

### Project structure
```
JobSearchAutomater/
├── src/
│   ├── models/          # Job, UserProfile, enums
│   ├── scrapers/        # Source adapters (one per company/source)
│   │   └── base.py      # Abstract BaseScraper interface
│   ├── persistence/     # SQLite database + repository
│   ├── normalizer/      # Raw → canonical Job transformation
│   ├── filters/         # Role/location rules engine
│   └── utils/           # URL cleaning, logging, config
├── tests/
│   ├── unit/
│   └── integration/
├── config/              # Source URLs, scraper settings
├── docs/
└── data/                # SQLite DB file, CSV exports
```
