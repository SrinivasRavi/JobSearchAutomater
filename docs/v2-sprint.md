# v2 Sprint — Human-Approved Apply Assistant

## Goal
Move from job discovery to job application. The system fills application forms using a UserProfile, with human review before submission.

## What v1 delivered (context for v2)
- 14 working scrapers across HTTP APIs and Playwright
- SQLite persistence with dedupe
- CLI for scrape/query/stats/export
- 1,200+ jobs in database
- Playwright already integrated

## v2 end-state
The user runs a CLI command. The system opens a visible browser, navigates to a job's application page, fills the form using UserProfile data, and pauses for human review. The user confirms or skips. The system records the result.

---

## Architecture Decisions (resolved)

### 1. Apply mechanism: Playwright headed mode (not Chrome extension)

**Decision**: Use Playwright in headed mode (visible browser window) for form filling.

**Why not a Chrome extension?**
- Chrome extensions require building a separate UI, manifest, content scripts, message passing, and packaging
- They need a separate local HTTP API server running simultaneously
- The extension can't be distributed via Chrome Web Store (private tool), so it needs manual sideloading
- Playwright is already integrated and working for scraping

**Why Playwright headed?**
- User can see exactly what the browser is doing
- Reuses existing Playwright infrastructure
- Human review = the user looks at the filled form in the visible browser, then confirms in terminal
- No separate API server needed for v2 (the CLI drives everything)
- Simpler to build, test, and debug

**How it works:**
1. CLI command: `python3 -m src.cli apply --job-id 42` or `python3 -m src.cli apply --next`
2. Playwright opens a visible Chromium window
3. Navigates to the job's application URL
4. ATS-specific filler fills the form fields
5. Terminal prints what was filled and asks: "Submit? [y/n/skip]"
6. On 'y': clicks submit, records APPLIED
7. On 'n': closes, records APPLY_FAILED with reason HUMAN_REJECTED
8. On 'skip': closes, no status change

### 2. UserProfile: YAML config file (not database)

**Decision**: Store UserProfile as a YAML file at `config/user_profile.yaml`.

**Why YAML, not DB?**
- UserProfile is static configuration, not runtime data
- User can edit it directly in their editor
- Only one profile needed for v2 (dreaming-doc explicitly says "one UserProfile only")
- No CRUD API needed
- Easy to version control (but .gitignore it since it contains PII)

**Schema:**
```yaml
# config/user_profile.yaml
name:
  first: "Srini"
  last: "Ravi"
email: "srini@example.com"
phone: "+91-XXXXXXXXXX"
location:
  city: "Mumbai"
  state: "Maharashtra"
  country: "India"
  zip: "400001"
resume_path: "config/resume.pdf"
linkedin_url: "https://linkedin.com/in/srini"
github_url: "https://github.com/SrinivasRavi"
portfolio_url: ""

# Work authorization
work_authorized: true
sponsorship_required: false
visa_status: ""

# Experience
years_of_experience: 5
current_company: ""
current_title: ""
notice_period_days: 30

# Education (most recent)
education:
  degree: "Bachelor of Engineering"
  major: "Computer Science"
  university: ""
  graduation_year: 2020

# Preferences (used for filtering, not form filling)
preferred_roles:
  - "Software Engineer"
  - "Backend Engineer"
  - "Software Developer"
salary_expectation: ""
willing_to_relocate: false

# Default answers for common ATS questions
default_answers:
  gender: "Prefer not to say"
  ethnicity: "Prefer not to say"
  veteran_status: "No"
  disability_status: "Prefer not to say"
```

### 3. ATS form fillers: Adapter pattern (like scrapers)

**Decision**: One form-filler class per ATS platform, registered in a filler registry.

**Why per-ATS?**
- Every ATS has different form structure, field names, required fields, and submission flow
- Workday forms look nothing like Greenhouse forms
- A generic "find all inputs and fill them" approach is too fragile
- The adapter pattern already works well for scrapers

**Registry design:**
```python
# Map of ATS platform name -> filler class
_FILLER_MAP: dict[str, type[BaseFormFiller]] = {}

def get_filler_for_url(url: str) -> Optional[BaseFormFiller]:
    """Detect ATS platform from URL and return appropriate filler."""
    # e.g., "*.myworkdayjobs.com" -> WorkdayFiller
    # e.g., "*.greenhouse.io" -> GreenhouseFiller
```

**ATS platforms to support (ordered by job count in our DB):**
1. **Oracle HCM** (JPMorgan, Oracle) — 625 jobs — highest priority
2. **Goldman Sachs custom** (higher.gs.com) — 273 jobs
3. **Workday** (Nasdaq) — 25 jobs
4. **Phenom People** (Morningstar) — 54 jobs
5. **SmartRecruiters** (Visa) — 17 jobs
6. **Google custom** — 16 jobs
7. **Microsoft/Eightfold** — 14 jobs
8. **TalentBrew** (Barclays, Citi) — 75 jobs (but apply link goes to different ATS)
9. **Adobe AEM** (BofA) — 4 jobs
10. **Others** as discovered

**Start with Oracle HCM and Workday** — they cover the most jobs and are well-documented platforms.

### 4. Application tracking: New `applications` table

**Decision**: Separate `applications` table (not reusing the jobs table status field).

**Why separate?**
- A job and an application are different entities (dreaming-doc section 10 agrees)
- Same job could have multiple attempts
- Need to track attempt metadata (timestamp, mode, error, screenshot)
- Jobs table stays clean for scraper concerns

**Schema:**
```sql
CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    status TEXT NOT NULL DEFAULT 'PENDING',
    -- PENDING, FORM_FILLED, SUBMITTED, FAILED, SKIPPED
    applied_timestamp TEXT,
    ats_platform TEXT,
    failure_reason TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE application_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL REFERENCES applications(id),
    attempt_timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    result TEXT NOT NULL,  -- SUCCESS, FAILED, SKIPPED
    error_message TEXT,
    screenshot_path TEXT
);
```

**Status flow:** Job.application_status still gets updated (APPLIED, APPLY_FAILED) for CLI queries, but the detailed tracking lives in the applications table.

### 5. ATS account management: Deferred to v2.1

**Decision**: Do NOT build account creation/management in initial v2.

**Why?**
- Many ATS platforms allow "apply without account" or use email-only flows
- Account creation adds significant complexity (email verification, password management, credential storage)
- The human is in the loop — they can create accounts manually when needed
- Build the form-filling pipeline first, add account management only when it becomes a blocker

**When a login wall is hit:** Record APPLY_FAILED with reason LOGIN_REQUIRED. The user deals with it manually.

### 6. Resume upload strategy

**Decision**: Playwright file chooser interception.

```python
# When a file input or "Upload Resume" button is detected:
page.set_input_files("input[type='file']", profile.resume_path)
# Or for drag-drop zones:
with page.expect_file_chooser() as fc_info:
    page.click("button:has-text('Upload')")
file_chooser = fc_info.value
file_chooser.set_files(profile.resume_path)
```

This is standard Playwright — no special infrastructure needed.

### 7. Screenshot capture for debugging

**Decision**: Take a screenshot before and after form fill, store in `data/screenshots/`.

```python
page.screenshot(path=f"data/screenshots/{job_id}_before.png")
# ... fill form ...
page.screenshot(path=f"data/screenshots/{job_id}_after.png")
```

Useful for debugging when a form fill goes wrong. Low cost, high value.

---

## Task Breakdown

Each task is self-contained and can be built independently. Tasks are ordered by dependency.

### Task 1: UserProfile model and config loader
**What**: Create `src/models/user_profile.py` with a UserProfile dataclass and a loader that reads `config/user_profile.yaml`.
**Files**:
- `src/models/user_profile.py` (new)
- `config/user_profile.example.yaml` (new — template without PII, committed to git)
- `tests/unit/test_user_profile.py` (new)
- `.gitignore` — add `config/user_profile.yaml`

**Interface**:
```python
@dataclass
class UserProfile:
    first_name: str
    last_name: str
    email: str
    phone: str
    city: str
    state: str
    country: str
    zip_code: str
    resume_path: str
    linkedin_url: str
    github_url: str
    portfolio_url: str
    work_authorized: bool
    sponsorship_required: bool
    years_of_experience: int
    current_company: str
    current_title: str
    notice_period_days: int
    degree: str
    major: str
    university: str
    graduation_year: int
    preferred_roles: list[str]
    default_answers: dict[str, str]

def load_user_profile(path: str = "config/user_profile.yaml") -> UserProfile:
    """Load UserProfile from YAML. Raises FileNotFoundError with helpful message if missing."""
```

**Tests**: Load from valid YAML, handle missing file, handle missing optional fields with defaults.
**Acceptance**: `UserProfile` loads from YAML, all fields accessible, missing file gives clear error.

---

### Task 2: Application persistence (DB schema + repository)
**What**: Add `applications` and `application_attempts` tables. Add repository methods.
**Files**:
- `src/persistence/database.py` — add tables to schema, add migration
- `src/persistence/repository.py` — add ApplicationRepository methods
- `tests/unit/test_application_repository.py` (new)

**Repository interface**:
```python
class ApplicationRepository:
    def create_application(self, job_id: int, ats_platform: str = "") -> int:
        """Create a new application record. Returns application_id."""

    def update_application_status(self, app_id: int, status: str,
                                   failure_reason: str = "", notes: str = ""):
        """Update application status."""

    def log_attempt(self, app_id: int, result: str,
                    error_message: str = "", screenshot_path: str = ""):
        """Log an application attempt."""

    def get_application_by_job_id(self, job_id: int) -> Optional[dict]:
        """Get application for a job, if exists."""

    def get_pending_jobs(self, limit: int = 10) -> list[dict]:
        """Get jobs that are NOT_APPLIED and have no application record."""

    def get_application_stats(self) -> dict:
        """Return counts by application status."""
```

**Tests**: Insert application, update status, log attempt, get pending jobs, get stats.
**Acceptance**: Schema creates cleanly on fresh DB and migrates existing DB. All CRUD works.

---

### Task 3: BaseFormFiller interface and filler registry
**What**: Define the abstract base class for form fillers and the registry that maps ATS platforms to filler classes.
**Files**:
- `src/applier/base.py` (new)
- `src/applier/registry.py` (new)
- `src/applier/__init__.py` (new)
- `tests/unit/test_filler_registry.py` (new)

**Interface**:
```python
class FillResult:
    success: bool
    fields_filled: list[str]  # names of fields that were filled
    fields_skipped: list[str]  # fields that couldn't be filled
    error: str

class BaseFormFiller(ABC):
    def __init__(self, profile: UserProfile):
        self.profile = profile

    @abstractmethod
    def platform_name(self) -> str:
        """Return ATS platform name (e.g., 'workday', 'oracle_hcm')."""

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this filler handles the given application URL."""

    @abstractmethod
    def fill_form(self, page: Page) -> FillResult:
        """Fill the application form on the current page. Do NOT submit."""

    @abstractmethod
    def submit(self, page: Page) -> bool:
        """Click the submit button. Return True if submission appeared successful."""
```

**Registry**:
```python
def get_filler_for_url(url: str, profile: UserProfile) -> Optional[BaseFormFiller]:
    """Detect ATS platform from URL and return appropriate filler instance."""
    for filler_class in _FILLER_MAP.values():
        instance = filler_class(profile)
        if instance.can_handle(url):
            return instance
    return None
```

**Tests**: Registry returns correct filler for known URLs, returns None for unknown.
**Acceptance**: Interface defined, registry works, no actual ATS filling yet.

---

### Task 4: Apply orchestrator (CLI → Playwright → filler → confirm)
**What**: The main apply loop that ties everything together.
**Files**:
- `src/applier/orchestrator.py` (new)
- `src/cli.py` — add `apply` command

**CLI commands**:
```bash
# Apply to a specific job by ID
python3 -m src.cli apply --job-id 42

# Apply to the next unapplied job
python3 -m src.cli apply --next

# Apply to next N unapplied jobs (batch mode, still confirms each)
python3 -m src.cli apply --next --limit 5

# Show application stats
python3 -m src.cli apply-stats
```

**Orchestrator flow**:
```python
class ApplyOrchestrator:
    def __init__(self, repo, app_repo, profile):
        ...

    def apply_to_job(self, job_id: int) -> ApplyResult:
        job = self.repo.get_by_id(job_id)
        filler = get_filler_for_url(job.job_link, self.profile)

        if not filler:
            return ApplyResult(status="UNSUPPORTED_ATS", ...)

        app_id = self.app_repo.create_application(job_id, filler.platform_name())

        with self._headed_browser() as page:
            page.goto(job.job_link)
            # Take before screenshot
            page.screenshot(path=f"data/screenshots/{job_id}_before.png")

            # Fill the form
            result = filler.fill_form(page)

            # Take after screenshot
            page.screenshot(path=f"data/screenshots/{job_id}_after.png")

            # Print summary to terminal
            print(f"Job: {job.job_title} at {job.company_name}")
            print(f"Fields filled: {result.fields_filled}")
            print(f"Fields skipped: {result.fields_skipped}")

            # Human confirmation
            choice = input("Submit? [y/n/skip]: ").strip().lower()

            if choice == 'y':
                submitted = filler.submit(page)
                # ... record result
            elif choice == 'n':
                # ... record HUMAN_REJECTED
            else:
                # ... skip, no status change
```

**Key detail**: `_headed_browser()` launches Playwright with `headless=False` so user sees the browser.

**Tests**: Mock-based tests for orchestrator flow (filler found/not found, user confirms/rejects/skips).
**Acceptance**: CLI command works end-to-end with a mock filler. Real ATS filling comes in Tasks 5+.

---

### Task 5: Oracle HCM form filler
**What**: First real ATS filler — handles Oracle HCM (used by JPMorgan, Oracle). This is the highest-value filler (625 jobs).
**Files**:
- `src/applier/oracle_hcm.py` (new)
- `tests/unit/test_oracle_hcm_filler.py` (new)

**Oracle HCM apply flow** (typical):
1. Job detail page has "Apply" button
2. Clicking it may ask for login or "Apply as Guest"
3. Guest flow: email → personal info form → resume upload → review → submit
4. Fields: first name, last name, email, phone, country, resume upload

**Implementation approach**:
- Click "Apply" button on job detail page
- If login wall: look for "Apply as Guest" or "Continue without signing in"
- If no guest option: return FAILED with LOGIN_REQUIRED
- Fill personal info fields by label text matching
- Upload resume via file input
- Stop before submit (human reviews)

**Selectors to use** (Oracle HCM is standardized):
```python
# These are common Oracle HCM selectors — verify during implementation
"input[aria-label*='First']"       # First name
"input[aria-label*='Last']"        # Last name
"input[aria-label*='Email']"       # Email
"input[aria-label*='Phone']"       # Phone
"input[type='file']"               # Resume upload
"button:has-text('Apply')"         # Apply button
"button:has-text('Submit')"        # Submit button
```

**Tests**: Unit tests with mocked Page object for field detection and filling logic.
**Acceptance**: Can fill an Oracle HCM application form on JPMorgan or Oracle careers. User sees filled form and confirms.

---

### Task 6: Workday form filler
**What**: Second ATS filler — handles Workday (used by Nasdaq, and many other companies).
**Files**:
- `src/applier/workday.py` (new)
- `tests/unit/test_workday_filler.py` (new)

**Workday apply flow** (typical):
1. Job page has "Apply" button
2. May ask to "Sign In" or "Apply Manually" / "Use My Last Application"
3. Form pages: "My Information" → "My Experience" → "Application Questions" → "Voluntary Disclosures" → "Self Identify" → "Review" → "Submit"
4. Multi-page wizard with "Next" / "Save and Continue" buttons

**Implementation approach**:
- Click "Apply" on job page
- Handle sign-in wall (look for "Apply Manually" or similar)
- Page 1 (My Information): first name, last name, email, phone, address, country
- Page 2 (My Experience): resume upload, education, work history
- Page 3+ (Questions): use default_answers from UserProfile for demographic questions
- Navigate pages with "Next" button
- Stop at review page for human confirmation

**Key challenge**: Workday has a multi-page wizard. The filler needs to handle page transitions.

**Tests**: Unit tests for each page's field detection.
**Acceptance**: Can fill a Workday application form on Nasdaq careers.

---

### Task 7: ATS URL detection and apply-link resolution
**What**: Many jobs in our DB have listing-page links, not application-page links. We need to resolve the actual "Apply" URL.
**Files**:
- `src/applier/url_resolver.py` (new)
- `tests/unit/test_url_resolver.py` (new)

**Problem**: Our scraped `job_link` often points to the job detail page, not the application form. The filler needs to:
1. Navigate to `job_link`
2. Find and click the "Apply" button
3. Handle any redirects or popups
4. Land on the actual application form

**Implementation**:
```python
class ApplyUrlResolver:
    def resolve_apply_page(self, page: Page, job_link: str) -> bool:
        """Navigate to job_link, find and click Apply button.
        Returns True if we landed on an application form."""
        page.goto(job_link, wait_until="domcontentloaded")

        # Try common "Apply" button selectors
        apply_selectors = [
            "button:has-text('Apply')",
            "a:has-text('Apply')",
            "button:has-text('Apply Now')",
            "a:has-text('Apply Now')",
            "[data-automation-id='apply']",
            # ... ATS-specific selectors
        ]
        for sel in apply_selectors:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_load_state("domcontentloaded")
                return True
        return False
```

**Tests**: Mock-based tests for button detection.
**Acceptance**: Resolver finds Apply button on job detail pages for Oracle HCM and Workday.

---

### Task 8: Apply-stats CLI and application review commands
**What**: CLI commands to view application progress and manage the apply queue.
**Files**:
- `src/cli.py` — add commands
- Update `docs/run-commands.md`

**Commands**:
```bash
# View application statistics
python3 -m src.cli apply-stats

# List jobs ready to apply (NOT_APPLIED, no application record)
python3 -m src.cli apply-queue --limit 20

# List past applications with status
python3 -m src.cli applications --status SUBMITTED
python3 -m src.cli applications --status FAILED

# Mark a job as manually applied (e.g., user applied outside the system)
python3 -m src.cli mark-applied --job-id 42
```

**Tests**: CLI arg parsing, output formatting.
**Acceptance**: User can see apply queue, past applications, and stats.

---

## Task Dependency Order

```
Task 1 (UserProfile)  ──┐
                         ├──→ Task 4 (Orchestrator + CLI) ──→ Task 5 (Oracle HCM filler)
Task 2 (Application DB) ─┤                                 → Task 6 (Workday filler)
                         │
Task 3 (Filler interface)┘
                                Task 7 (URL resolver) — can be built alongside Task 5/6
                                Task 8 (CLI stats)     — can be built alongside Task 5/6
```

**Build order**: Tasks 1, 2, 3 can be built in parallel. Task 4 depends on all three. Tasks 5-8 depend on Task 4.

## Implementation Notes for Sonnet

### General
- Follow existing patterns: look at `src/scrapers/base.py` for the adapter pattern, `src/persistence/repository.py` for DB access patterns, `src/cli.py` for CLI patterns.
- Use TDD: write tests first, then implement.
- Use `python3` not `python` in all commands.
- Activate venv before running anything: `source .venv/bin/activate`
- All Playwright usage should follow the pattern in `src/scrapers/playwright_base.py`.
- Keep functions small. Log errors with enough context.
- Do not add features beyond what the task specifies.

### Testing
- Mock Playwright Page objects in unit tests — don't launch real browsers in tests.
- For integration tests of real ATS filling, create a separate `tests/integration/` directory.
- Unit tests should run fast (<1s).

### Important constraints
- v2 is ONE UserProfile only. Do not build multi-profile support.
- Human-in-the-loop is REQUIRED. Never auto-submit without terminal confirmation.
- When a form can't be filled (login wall, CAPTCHA, unsupported ATS): fail gracefully, record the reason, move on.
- Screenshots go in `data/screenshots/` — add this to `.gitignore`.
- `config/user_profile.yaml` contains PII — must be in `.gitignore`.

### What NOT to build in v2
- Account creation on ATS platforms
- Cover letter generation
- Multi-profile support
- Autopilot (zero-click) mode
- Chrome extension
- Local HTTP API server
- Job scoring or ranking
- Email tracking / outcome monitoring

---

## Acceptance Criteria for v2

v2 is done when:
1. User can run `python3 -m src.cli apply --next` and see a visible browser fill a real application form
2. User reviews the filled form and confirms/rejects in terminal
3. Application status is recorded in the database
4. At least Oracle HCM and Workday ATS platforms are supported
5. Unsupported ATS platforms fail gracefully with a clear message
6. `apply-stats` and `apply-queue` CLI commands work
7. Screenshots are captured for debugging
8. All unit tests pass
