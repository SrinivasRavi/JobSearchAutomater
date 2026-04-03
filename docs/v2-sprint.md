# v2 Sprint — Human-Approved Apply Assistant

## Goal
Move from job discovery to job application. The system fills application forms using a UserProfile, with human review before submission.

**Primary flow (v2):** CLI batch — system picks jobs from the queue, opens a visible browser, fills the form, user confirms in terminal.

**Secondary flow (later):** Chrome extension — user discovers a job themselves, clicks the extension, picks a UserProfile, extension fills the form in-page. This will be built independently and integrated later.

## What v1 delivered (context for v2)
- 14 working scrapers across HTTP APIs and Playwright
- SQLite persistence with dedupe
- CLI for scrape/query/stats/export
- 1,200+ jobs in database
- Playwright already integrated

## v2 end-state
User runs `python3 -m src.cli apply --next`. System opens a visible Chromium window, navigates to the job's application page, fills the form using the selected UserProfile, and pauses. User reviews the filled form in the browser, then confirms/skips in the terminal. System records the result.

---

## Architecture Decisions (resolved)

### 1. Apply mechanism: Playwright headed mode

**Decision**: Use Playwright in headed mode (visible browser window) for form filling.

**Why?**
- User can see exactly what the browser is doing
- Reuses existing Playwright infrastructure (already working for scraping)
- Human review = user looks at the filled form in the visible browser, confirms in terminal
- Simpler to build, test, and debug than a Chrome extension
- No separate API server needed — the CLI drives everything

**How it works:**
1. CLI command: `python3 -m src.cli apply --job-id 42` or `python3 -m src.cli apply --next`
2. Playwright opens a visible Chromium window
3. Navigates to the job's application URL
4. ATS-specific filler fills the form fields
5. Terminal prints what was filled and asks: "Submit? [y/n/skip]"
6. On 'y': clicks submit, records APPLIED
7. On 'n': closes, records APPLY_FAILED with reason HUMAN_REJECTED
8. On 'skip': closes, no status change

### 2. UserProfile: Multiple YAML files

**Decision**: Store each UserProfile as a separate YAML file in `config/profiles/`.

```
config/profiles/
├── example.yaml          (template, committed to git)
├── backend_mumbai.yaml   (real profile, gitignored)
├── ai_remote.yaml        (real profile, gitignored)
└── backend_bangalore.yaml
```

**Why multiple files?**
- User wants to compare profiles quickly (open two files side by side)
- Each file is self-contained — easy to create a new profile by copying
- No multi-profile DB schema needed — just glob the directory
- `.gitignore` the real files (PII), commit only `example.yaml`

**Schema (each file):** (please use the other schema and sample profile given after this)
```yaml
# config/profiles/backend_mumbai.yaml
profile_name: "Backend Mumbai"

name:
  first: "Srini"
  last: "Ravi"
email: "srini.backend@example.com"
phone: "+91-XXXXXXXXXX"

location:
  city: "Mumbai"
  state: "Maharashtra"
  country: "India"
  zip: "400001"

resume_path: "config/resumes/backend_resume.pdf"
linkedin_url: "https://linkedin.com/in/srini"
github_url: "https://github.com/SrinivasRavi"
portfolio_url: ""

work_authorized: true
sponsorship_required: false

years_of_experience: 5
current_company: ""
current_title: ""
notice_period_days: 30

education:
  degree: "Bachelor of Engineering"
  major: "Computer Science"
  university: ""
  graduation_year: 2020

preferred_roles:
  - "Software Engineer"
  - "Backend Engineer"
  - "Software Developer"

default_answers:
  gender: "Prefer not to say"
  ethnicity: "Prefer not to say"
  veteran_status: "No"
  disability_status: "Prefer not to say"
```

new sample profile (use this schema and sample profile instead. Replace Mumbai with Pune everywhere for the 2nd UserProfile)
```yaml
profile_id: backend_mumbai
profile_name: Backend Mumbai

first_name: Srinivas
last_name: Ravi
full_name: Srinivas Ravi

email: srinivasravi404@gmail.com
phone: "+917208816364"

location:
  city: Mumbai
  state: Maharashtra
  country: India
  zip_code: "400706"

links:
  linkedin_url: "https://linkedin.com/in/srinivas-ravi"
  github_url: "https://github.com/SrinivasRavi"
  portfolio_url: ""

employment:
  years_of_experience: 7
  notice_period_days: 0

experience:
  - company: "Salesforce Inc"
    title: "Senior Member of Technical Staff"
    from: "29/04/2022"
    to: "21/08/2024"
    currently_working_here: false
  - company: "Amazon Inc."
    title: "Software Development Engineer"
    from: "19/08/2019"
    to: "21/04/2022"
    currently_working_here: false

education:
  - degree: "MS"
    major: "Computer Science"
    university: "University at Buffalo"
    graduation_year: 2019
  - degree: "BE"
    major: "Computer Engineering"
    university: "Mumbai University"
    graduation_year: 2015

work_preferences:
  target_roles:
    - Backend Engineer
    - Software Engineer
    - Java Developer
  target_locations:
    - Mumbai

documents:
  resume_file_name: "backend_resume.pdf"
  resume_path_hint: "/Users/srinivasravi/dev/JobSearchAutomater/docs/backend_resume.pdf"

custom_answers:
  sponsorship_required: "No"
  authorized_to_work: "Yes"
  current_ctc: ""
  expected_ctc: "30 LPA"
```

### 3. ATS form fillers: Adapter pattern (like scrapers)

**Decision**: One form-filler class per ATS platform, registered in a filler registry.

**Why per-ATS?**
- Every ATS has different form structure, field names, required fields, and submission flow
- Workday forms look nothing like Greenhouse forms
- A generic "find all inputs and fill them" approach is too fragile for Playwright
- The adapter pattern already works well for scrapers

**Registry design:**
```python
_FILLER_MAP: dict[str, type[BaseFormFiller]] = {}

def get_filler_for_url(url: str, profile: UserProfile) -> Optional[BaseFormFiller]:
    """Detect ATS platform from URL and return appropriate filler."""
```

**ATS platforms to support (ordered by job count in our DB):**
1. **Oracle HCM** (JPMorgan, Oracle) — 625 jobs — highest priority
2. **Workday** (Nasdaq + many other companies) — 25 jobs but very common platform
3. **Others** as needed

**Start with Oracle HCM and Workday.**

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
    job_id INTEGER REFERENCES jobs(id),
    profile_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    -- PENDING, FORM_FILLED, SUBMITTED, FAILED, SKIPPED
    applied_timestamp TEXT,
    ats_platform TEXT,
    job_url TEXT,
    job_title TEXT,
    company_name TEXT,
    failure_reason TEXT,
    apply_method TEXT NOT NULL DEFAULT 'cli',  -- 'cli' or 'extension'
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

**Note**: `job_id` is nullable to support extension-applied jobs that may not exist in our scraped DB. `job_url`/`job_title`/`company_name` are stored directly for attribution. `profile_name` tracks which profile was used. `apply_method` distinguishes CLI vs extension.

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
page.set_input_files("input[type='file']", profile.resume_path)
```

Standard Playwright — no special infrastructure needed.

### 7. Screenshot capture for debugging

**Decision**: Take a screenshot before and after form fill, store in `data/screenshots/`.

```python
page.screenshot(path=f"data/screenshots/{job_id}_before.png")
# ... fill form ...
page.screenshot(path=f"data/screenshots/{job_id}_after.png")
```

---

## Task Breakdown

### Phase A: Shared Backbone (Tasks 1-3, parallelizable)

#### Task 1: UserProfile model and multi-profile loader
**What**: UserProfile dataclass + loader for `config/profiles/*.yaml`.
**Files**:
- `src/models/user_profile.py` (new)
- `config/profiles/example.yaml` (new — template without PII, committed to git)
- `tests/unit/test_user_profile.py` (new)
- `.gitignore` — add `config/profiles/*.yaml`, `!config/profiles/example.yaml`

**Interface**:
```python
@dataclass
class UserProfile:
    profile_name: str
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

    def summary(self) -> str:
        """One-line summary: 'Backend Mumbai (srini.backend@example.com)'"""

    def to_dict(self) -> dict:
        """For JSON serialization."""

def load_profile(name: str) -> UserProfile:
    """Load config/profiles/{name}.yaml. Raises FileNotFoundError if missing."""

def list_profiles() -> list[tuple[str, str]]:
    """Return [(profile_name, summary), ...] for all profiles in config/profiles/."""
```

**Tests**: Load profile, list profiles, handle missing file, handle missing optional fields with defaults, to_dict round-trip.
**Acceptance**: Multiple profiles load correctly, summaries are human-readable.

---

#### Task 2: Application persistence (DB schema + repository)
**What**: Add `applications` and `application_attempts` tables with repository methods.
**Files**:
- `src/persistence/database.py` — add tables to schema + migration
- `src/persistence/repository.py` — add ApplicationRepository
- `tests/unit/test_application_repository.py` (new)

**Repository interface**:
```python
class ApplicationRepository:
    def create_application(self, job_id: Optional[int], profile_name: str,
                           job_url: str, job_title: str = "", company_name: str = "",
                           ats_platform: str = "", apply_method: str = "cli") -> int:

    def update_status(self, app_id: int, status: str,
                      failure_reason: str = "", notes: str = ""):

    def log_attempt(self, app_id: int, result: str,
                    error_message: str = "", screenshot_path: str = ""):

    def get_by_job_id(self, job_id: int) -> Optional[dict]:

    def get_pending_jobs(self, limit: int = 10) -> list[dict]:
        """Jobs that are NOT_APPLIED and have no application record."""

    def get_stats(self) -> dict:
        """Counts by status, by profile, by method."""

    def list_applications(self, status: Optional[str] = None,
                          profile: Optional[str] = None, limit: int = 50) -> list[dict]:
```

**Tests**: CRUD operations, nullable job_id, stats aggregation, pending jobs query.
**Acceptance**: Schema creates/migrates cleanly. All methods work.

---

#### Task 3: BaseFormFiller interface and filler registry
**What**: Abstract base class for per-ATS Python form fillers + registry.
**Files**:
- `src/applier/__init__.py` (new)
- `src/applier/base.py` (new)
- `src/applier/registry.py` (new)
- `tests/unit/test_filler_registry.py` (new)

**Interface**:
```python
@dataclass
class FillResult:
    success: bool
    fields_filled: list[str]
    fields_skipped: list[str]
    error: str = ""

class BaseFormFiller(ABC):
    def __init__(self, profile: UserProfile):
        self.profile = profile

    @abstractmethod
    def platform_name(self) -> str: ...

    @abstractmethod
    def can_handle(self, url: str) -> bool: ...

    @abstractmethod
    def fill_form(self, page: Page) -> FillResult: ...

    @abstractmethod
    def submit(self, page: Page) -> bool: ...

def get_filler_for_url(url: str, profile: UserProfile) -> Optional[BaseFormFiller]:
    """Detect ATS from URL, return filler instance."""
```

**Tests**: Registry lookup, can_handle detection, None for unknown URLs.
**Acceptance**: Interface compiles, registry works.

---

### Phase B: CLI Apply Flow (Task 4, depends on Phase A)

#### Task 4: Apply orchestrator + CLI commands
**What**: The CLI apply loop: pick job → Playwright headed → fill → confirm in terminal.
**Files**:
- `src/applier/orchestrator.py` (new)
- `src/cli.py` — add `apply`, `apply-stats`, `apply-queue`, `mark-applied`, `list-profiles` commands

**CLI commands**:
```bash
python3 -m src.cli apply --job-id 42                      # Apply to specific job
python3 -m src.cli apply --job-id 42 --profile ai_remote  # With specific profile
python3 -m src.cli apply --next                            # Next unapplied job
python3 -m src.cli apply --next --limit 5                  # Next 5 (confirms each)
python3 -m src.cli apply-queue --limit 20                  # Show apply queue
python3 -m src.cli apply-stats                             # Application statistics
python3 -m src.cli applications --status SUBMITTED         # List past applications
python3 -m src.cli mark-applied --job-id 42                # Mark as manually applied
python3 -m src.cli list-profiles                           # Show available profiles
```

**Orchestrator flow**:
1. Load profile (default: first profile in `config/profiles/`, or `--profile` flag)
2. Get job from DB
3. Find filler for job URL (or fail with UNSUPPORTED_ATS)
4. Launch Playwright headed (`headless=False`)
5. Navigate to job URL, take before-screenshot
6. Fill form, take after-screenshot
7. Print summary to terminal (job title, company, fields filled/skipped)
8. Prompt: "Submit? [y/n/skip]"
9. Record result in applications table + update job status

**Tests**: Mock-based orchestrator tests. Confirm/reject/skip paths. Filler found/not found.
**Acceptance**: End-to-end CLI flow works with a mock filler.

---

### Phase C: Per-ATS Fillers (Tasks 5-6, depend on Phase B)

#### Task 5: Oracle HCM form filler
**What**: First real ATS filler — handles Oracle HCM (used by JPMorgan, Oracle). Highest-value filler (625 jobs).
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

**Selectors** (Oracle HCM is standardized):
```python
"input[aria-label*='First']"       # First name
"input[aria-label*='Last']"        # Last name
"input[aria-label*='Email']"       # Email
"input[aria-label*='Phone']"       # Phone
"input[type='file']"               # Resume upload
"button:has-text('Apply')"         # Apply button
"button:has-text('Submit')"        # Submit button
```

**Tests**: Unit tests with mocked Page object for field detection and filling logic.
**Acceptance**: Can fill an Oracle HCM application form on JPMorgan or Oracle careers.

---

#### Task 6: Workday form filler
**What**: Second ATS filler — handles Workday (used by Nasdaq + many other companies).
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

### Phase D: Polish (Tasks 7-8, depend on Phase B)

#### Task 7: ATS URL detection and apply-link resolution
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
        apply_selectors = [
            "button:has-text('Apply')",
            "a:has-text('Apply')",
            "button:has-text('Apply Now')",
            "a:has-text('Apply Now')",
            "[data-automation-id='apply']",
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
**Acceptance**: Resolver finds Apply button on Oracle HCM and Workday job detail pages.

---

#### Task 8: Apply-stats CLI and run-commands update
**What**: Ensure all apply-related CLI commands work and update run-commands.md.
**Files**:
- `src/cli.py` — verify all commands from Task 4
- `docs/run-commands.md` — add v2 commands section

**Acceptance**: User can see apply queue, past applications, stats, and available profiles.

---

## Task Dependency Graph

```
Phase A (parallel):
  Task 1 (UserProfile)  ──┐
  Task 2 (Application DB) ─┼──→ Phase B: Task 4 (CLI Orchestrator)
  Task 3 (Filler base)  ──┘         │
                                     ├──→ Phase C: Task 5 (Oracle HCM filler)
                                     │              Task 6 (Workday filler)
                                     └──→ Phase D: Task 7 (URL resolver)
                                                    Task 8 (CLI polish + docs)
```

**Build order for Sonnet:**
1. Tasks 1, 2, 3 (parallel, no dependencies)
2. Task 4 (CLI orchestrator — core flow)
3. Tasks 5, 6 (per-ATS fillers — make it actually useful)
4. Tasks 7, 8 (polish)

---

## Implementation Notes for Sonnet

### General
- Follow existing patterns: `src/scrapers/base.py` for adapters, `src/persistence/repository.py` for DB, `src/cli.py` for CLI.
- Use TDD: write tests first, then implement.
- Use `python3` not `python`. Activate venv first: `source .venv/bin/activate`
- All Playwright usage should follow the pattern in `src/scrapers/playwright_base.py`.
- Keep functions small. Log errors with enough context.
- Do not add features beyond what the task specifies.
- Commit and push after completing each task.

### Testing
- Mock Playwright Page objects in unit tests — don't launch real browsers in tests.
- For integration tests of real ATS filling, create a separate `tests/integration/` directory.
- Unit tests should run fast (<1s).

### Important constraints
- Human-in-the-loop is REQUIRED. Never auto-submit without terminal confirmation.
- When a form can't be filled (login wall, CAPTCHA, unsupported ATS): fail gracefully, record the reason, move on.
- Screenshots go in `data/screenshots/` — add this to `.gitignore`.
- `config/profiles/*.yaml` contains PII — must be in `.gitignore` (except `example.yaml`).

### What NOT to build in v2
- Account creation on ATS platforms (deferred to v2.1)
- Cover letter generation
- Autopilot (zero-click) mode
- Chrome extension or local API server (built separately)
- Job scoring or ranking
- Email tracking / outcome monitoring

---

## Acceptance Criteria for v2

v2 is done when:
1. `python3 -m src.cli apply --next` opens a visible browser and fills a real application form
2. User reviews the filled form and confirms/rejects in terminal
3. Application status is recorded in the database
4. At least Oracle HCM and Workday ATS platforms are supported
5. Unsupported ATS platforms fail gracefully with a clear message
6. Multiple UserProfiles work (different YAML files, selectable via `--profile`)
7. `apply-stats`, `apply-queue`, and `list-profiles` CLI commands work
8. Screenshots are captured for debugging
9. All unit tests pass

---

## Appendix: Independent Chrome Extension Build Spec

This section describes a standalone Chrome extension that reads a YAML-format UserProfile and auto-fills job application forms. It is built independently of the Python codebase above.

### Purpose
A Chrome Manifest V3 extension that:
1. Lets the user load/select a UserProfile (from a YAML file or pasted YAML text)
2. On any job application page, fills visible form fields using the selected profile
3. Does NOT submit — the user always reviews and submits manually

### Extension structure
```
job-autofiller-extension/
├── manifest.json
├── popup.html
├── popup.js
├── popup.css
├── content.js
├── field_map.js
├── yaml_parser.js       (lightweight YAML parser, e.g., js-yaml via CDN or bundled)
└── icons/
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

### manifest.json
```json
{
  "manifest_version": 3,
  "name": "Job Application Autofiller",
  "version": "0.1.0",
  "description": "Auto-fill job application forms from a YAML profile",
  "permissions": ["activeTab", "scripting", "storage"],
  "action": {
    "default_popup": "popup.html",
    "default_icon": "icons/icon48.png"
  }
}
```

Note: No `content_scripts` in manifest — inject via `chrome.scripting.executeScript` on demand (only when user clicks "Fill"). This avoids injecting into every page.

### UserProfile YAML schema
Same schema as the Python codebase (see section 2 above). The extension parses this YAML client-side.

### Popup UI (`popup.html` + `popup.js`)

**Layout:**
1. **Profile selector**: Dropdown of saved profiles (stored in `chrome.storage.local`)
2. **Import button**: "Import Profile" — opens a file picker for a `.yaml` file, parses it, saves to storage
3. **Profile summary**: Shows the selected profile's key fields (name, email, resume filename) so user can quickly verify which profile is active
4. **"Fill Form" button**: Injects content script into the active tab and sends profile data
5. **Status area**: After fill, shows "Filled X fields, skipped Y fields"
6. **"Delete Profile" link**: Removes the selected profile from storage

**Profile storage:**
```javascript
// Save parsed profile to chrome.storage.local
chrome.storage.local.set({
  profiles: {
    backend_mumbai: { profile_name: "Backend Mumbai", first_name: "Srini", ... },
    ai_remote: { profile_name: "AI Remote", first_name: "Srini", ... }
  },
  active_profile: "backend_mumbai"
});
```

### Content script (`content.js`)

**Injected on demand** when user clicks "Fill Form":
```javascript
chrome.scripting.executeScript({
  target: { tabId: activeTab.id },
  files: ['field_map.js', 'content.js']
});
```

Then send profile data via messaging:
```javascript
chrome.tabs.sendMessage(activeTab.id, {
  action: 'fill',
  profile: selectedProfileData
});
```

### Field mapping (`field_map.js`)

Generic label-matching approach:
```javascript
const FIELD_MAP = [
  { patterns: [/first\s*name/i, /given\s*name/i, /fname/i], field: 'first_name' },
  { patterns: [/last\s*name/i, /family\s*name/i, /surname/i, /lname/i], field: 'last_name' },
  { patterns: [/e-?mail/i], field: 'email' },
  { patterns: [/phone/i, /mobile/i, /tel(?:ephone)?/i], field: 'phone' },
  { patterns: [/city/i, /town/i], field: 'city' },
  { patterns: [/state/i, /province/i, /region/i], field: 'state' },
  { patterns: [/country/i], field: 'country' },
  { patterns: [/zip/i, /postal/i, /pin\s*code/i], field: 'zip_code' },
  { patterns: [/linkedin/i], field: 'linkedin_url' },
  { patterns: [/github/i], field: 'github_url' },
  { patterns: [/portfolio/i, /website/i, /personal.*url/i], field: 'portfolio_url' },
  { patterns: [/years?\s*(of\s*)?exp/i], field: 'years_of_experience' },
  { patterns: [/current\s*(company|employer)/i], field: 'current_company' },
  { patterns: [/current\s*(title|position|role)/i], field: 'current_title' },
  { patterns: [/notice\s*period/i], field: 'notice_period_days' },
  { patterns: [/degree/i], field: 'degree' },
  { patterns: [/major|field\s*of\s*study/i], field: 'major' },
  { patterns: [/university|school|college|institution/i], field: 'university' },
  { patterns: [/graduat/i, /year.*complet/i], field: 'graduation_year' },
];
```

### Label detection logic

For each `<input>`, `<textarea>`, `<select>` on the page:
1. Check `<label for="id">` association
2. Check `aria-label` attribute
3. Check `placeholder` attribute
4. Check `name` attribute
5. Walk up the DOM to find nearest text node (handles cases like `<div><span>First Name</span><input/></div>`)
6. Match the found label text against FIELD_MAP patterns

### Value setting (React/Angular/Vue compatible)

Must dispatch proper events so SPA frameworks register the change:
```javascript
function setInputValue(input, value) {
  // Use native setter to bypass React's synthetic event system
  const nativeSet = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, 'value'
  ).set;
  nativeSet.call(input, String(value));
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
  input.dispatchEvent(new Event('blur', { bubbles: true }));
}
```

For `<select>` elements: find the `<option>` whose text best matches the profile value, set `selectedIndex`, dispatch `change`.

For `<textarea>`: same as input but use `HTMLTextAreaElement.prototype`.

### Dropdowns that aren't real `<select>` elements

Many ATS platforms use custom dropdown components (React Select, Material UI, etc.). For these:
1. Click the dropdown trigger to open it
2. Look for the options list that appears
3. Find the option matching the profile value
4. Click it

This is harder to make generic. For v1 of the extension, skip these and show them in "skipped fields". The user fills them manually.

### Resume upload

The extension CANNOT auto-upload files from a path (browser security). Instead:
- Detect `<input type="file">` on the page
- Show in the popup: "Resume to upload: backend_resume.pdf (from ~/path/to/resume)"
- The user clicks the file input and selects the file manually

### What the extension does NOT do
- Auto-submit (user always clicks submit themselves)
- Handle multi-page wizards automatically (user navigates pages, clicks "Fill" on each)
- Handle CAPTCHA or login walls
- Communicate with any backend server (fully standalone)
- Track applications in a database (it's a pure form-filler)

### Testing
- Load unpacked in Chrome: `chrome://extensions` → Developer mode → Load unpacked
- Test on real application pages: Workday, Oracle HCM, Greenhouse, Lever, SmartRecruiters
- Verify field filling + event dispatching (check that the form's internal state updates, not just visual)

### Future integration with JobSearchAutomater
When this extension is later integrated with the main Python project:
- Add a FastAPI local server (`localhost:8787`) that serves profiles and logs applications
- Extension calls the API instead of using `chrome.storage.local`
- Application tracking flows into the shared SQLite database
- This is a v2.1+ concern, not needed for the standalone extension
