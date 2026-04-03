# v2 Sprint — Human-Approved Apply Assistant

## Status
- **Started**: 2026-04-02
- **Last updated**: 2026-04-03
- **Phase A-B**: Complete (backbone, CLI, persistence)
- **Phase C**: In progress — Workday filler fills My Information page end-to-end
- **Current blocker**: Multi-page wizard (Pages 4-7) not yet handled; phone format validation error

---

## Goal
Move from job discovery to job application. The system fills application forms using a UserProfile, with human review before submission.

**Primary flow**: CLI batch — system picks jobs from the queue, opens a visible browser, fills the form, user confirms in terminal.

## What v1 delivered
- 14 working scrapers (HTTP + Playwright)
- SQLite persistence with dedupe
- CLI for scrape/query/stats/export
- 1,200+ jobs in database
- Playwright already integrated

---

## What v2 has built so far

### Working
1. **UserProfile model** — YAML-based profiles in `config/profiles/*.yaml`, with full schema (identity, location, links, experience, education, custom_answers, ats_password)
2. **Application persistence** — `applications` + `application_attempts` tables, `ApplicationRepository` with CRUD + stats
3. **Filler framework** — `BaseFormFiller` ABC, `FillResult` dataclass, filler registry with `can_handle()` URL matching
4. **CLI commands** — `apply` (--next, --job-id, --job-link, --company, --profile, --limit), `apply-queue`, `apply-stats`, `applications`, `mark-applied`, `list-profiles`
5. **Orchestrator** — Opens visible Chromium, two-step prompt (Proceed? → Submit?), records results
6. **Workday filler — full My Information page fill** — Complete flow:
   - Click Apply button (force=True for Workday overlay)
   - Handle "Apply Manually" modal (if present)
   - Detect account page via password field count (2 = Create Account, 1 = Sign In)
   - Sign In preferred: click "Sign In" link → detect modal dialog → scope selectors to modal → fill email + password → click Sign In
   - Create Account fallback: fill email + 2 passwords + consent checkbox → click Create Account
   - Wait for My Information page (using form field indicators, not progress bar text)
   - Scroll to reveal all lazy-loaded fields
   - Fill: first_name, last_name, phone (country code stripped), city, zip_code, address
   - Click "No" radio for "Previously worked for Nasdaq?"
7. **Oracle HCM filler** — Basic navigation (Apply → guest/login), field filling (untested on real site)

### Key Workday learnings (from self-testing)
- **Workday is an SPA**: Old page DOM stays in the DOM behind new pages. Must scope selectors carefully.
- **Sign In appears as a modal dialog**: `[role='dialog']` overlay on top of Create Account page. Selectors must scope to modal.
- **`text=My Information` is a false positive**: Progress bar text appears on ALL pages. Use actual form field IDs instead.
- **Form fields use `name=` and `id=` attributes**: NOT `data-automation-id` or `aria-label` on the My Information page.
- **Phone field is split**: Country code dropdown + local number. Must strip `+91-` prefix before filling.
- **`networkidle` times out on page.goto**: Use `domcontentloaded` + manual wait instead.

### Not working / remaining
1. **Phone number format**: Workday validates phone format — current value triggers "Enter a valid format" error. Need to investigate correct format.
2. **"How Did You Hear About Us?" dropdown**: Custom Workday dropdown (not `<select>`), currently skipped. Human fills manually.
3. **Multi-page wizard (Pages 4-7)**: No handling for My Experience → Application Questions → Voluntary Disclosures → Review
4. **Resume upload**: Not tested on My Experience page yet
5. **Most companies unsupported** — Only Workday and Oracle HCM fillers exist

---

## Workday Application Flow (learned from real Nasdaq testing)

This is the actual multi-step flow observed on `nasdaq.wd1.myworkdayjobs.com`:

### Page 0: Job Detail
- URL: `nasdaq.wd1.myworkdayjobs.com/Global_External_Site/job/...`
- Action: Click "Apply" button (teal, prominent)
- Wait: 3s for SPA modal to render

### Page 1: "Start Your Application" Modal
- Overlay on job detail page
- Options: "Autofill with Resume", "Apply Manually", "Use My Last Application", "Apply with SEEK", "Apply With LinkedIn"
- Action: Click "Apply Manually"
- Wait: networkidle + 3s for page transition

### Page 2: Create Account / Sign In
- URL changes to include `/en-US/` path
- Progress bar: "Create Account/Sign In" → My Information → My Experience → Application Questions → Voluntary Disclosures → Review
- Fields: Email Address, Password, Verify New Password
- Checkbox: "Yes, I have read and consent to the terms and conditions"
- Button: "Create Account" (or "Sign In" link if account exists)
- **If account already exists**: Click "Sign In" link → email + password → click "Sign In"
- Wait: networkidle + 5s (account creation takes time)

### Page 3: My Information
- Progress bar: active on "My Information"
- Fields:
  - "How Did You Hear About Us?" (custom dropdown with search — NOT a `<select>`)
  - "Have you previously worked for Nasdaq?" (radio: Yes/No)
  - Country (dropdown, pre-filled as India)
  - **Legal Name section**: Given Name(s), Family Name(s)
  - Possibly: Address, Phone, Email
- Button: "Save and Continue"
- Wait: networkidle + 3s

### Page 4: My Experience
- Resume upload (file input)
- Work History (may have add/edit forms)
- Education (may have add/edit forms)
- Button: "Save and Continue"

### Page 5: Application Questions
- Company-specific questions (varies per job)
- May include: current CTC, expected CTC, notice period, referral
- Button: "Save and Continue"

### Page 6: Voluntary Disclosures
- Optional demographic questions: gender, ethnicity, veteran status, disability
- Button: "Save and Continue"

### Page 7: Review
- Summary of all entered information
- Button: "Submit Application"
- **This is where human confirms in terminal**

---

## Remaining Tasks (Priority Order)

### Task C1: Fix Create Account button click (CURRENT BLOCKER)
**Problem**: The "Create Account" button is found and appears to be clicked, but the page doesn't advance. The `_wait_and_click` method silently catches all exceptions, masking errors.

**Investigation needed**:
- Add detailed error logging to `_wait_and_click` (log the actual exception)
- Check if the button is actually a `<button>` or some other element (`<div>`, `<a>`)
- Check if form validation errors appear after click (password too weak, email taken)
- Try using `page.locator().click()` (Playwright's newer auto-waiting API) instead of `wait_for_selector().click()`
- Try scrolling the button into view before clicking
- Try `page.click(selector)` directly

**Acceptance**: After filling Create Account form, the page advances to "My Information"

### Task C2: Handle "Sign In" flow (alternative to Create Account)
**Problem**: Once an account is created, subsequent attempts should Sign In, not Create Account. The Sign In page has: email, password, Sign In button.

**Already partially coded** in `_handle_sign_in()`. Needs:
- Test with a real already-registered email
- Handle "incorrect password" error gracefully
- Handle "account locked" scenario

### Task C3: Fill "My Information" page (Page 3)
**What**: Fill the form fields on the My Information page after account creation/sign-in.

**Challenges**:
- "How Did You Hear About Us?" — Workday custom dropdown (not `<select>`). Need to: click the trigger, wait for options list, type/search, click matching option. Or skip and let human fill.
- "Previously worked for Nasdaq?" — Radio buttons. Need `page.click("label:has-text('No')")` or similar.
- Country — Dropdown, may be pre-filled. Need to verify or set.
- Given Name / Family Name — Standard text inputs (should work with existing `_FIELD_SELECTORS`)

**Approach**: Fill what we can (text inputs), skip what we can't (custom dropdowns), report to user.

**Acceptance**: Given Name and Family Name filled. Human fills dropdowns/radios manually before clicking "Save and Continue".

### Task C4: Navigate multi-page wizard
**What**: After human reviews Page 3 and clicks "Save and Continue", the filler should:
1. Wait for the next page to load
2. Fill what it can on that page
3. Report filled/skipped to terminal
4. Wait for human to review and click "Save and Continue" again
5. Repeat until Review page

**Key decision**: Should the filler try to auto-navigate (click "Save and Continue" itself) or should the human drive page navigation?

**Recommendation**: Human drives navigation for now. The filler fills fields on whatever page is currently showing. When the human is satisfied, they click "Save and Continue" in the browser. The terminal prompt only appears on the final Review page for "Submit? [y/n/skip]".

**This requires changing the orchestrator flow**:
- Current: fill_form → prompt → submit
- New: fill_form → user navigates pages in browser → user reaches Review → prompt → submit

One approach: After initial fill, show "Navigating pages. Fill fields as needed. Press Enter when on Review page..." in terminal. Then prompt Submit.

### Task C5: Resume upload on "My Experience" page
**What**: Upload resume file on the My Experience page.

**Already coded** but untested:
```python
file_el = page.query_selector("input[type='file']")
if file_el and file_el.is_visible():
    page.set_input_files("input[type='file']", profile.resume_path_hint)
```

**Needs**: Verification that the file input is accessible on the My Experience page. Workday may use a drag-and-drop uploader or hidden file input.

### Task C6: Oracle HCM end-to-end (JPMorgan)
**What**: Test and fix the Oracle HCM filler on real JPMorgan job URLs.

**Expected flow** (needs investigation):
1. Job detail → Click Apply
2. Login/Guest page → Navigate
3. Form pages → Fill fields
4. Submit

**Deferred until Workday is working end-to-end.**

---

## Architecture Decisions

### Resolved
1. **Playwright headed mode** for form filling (visible browser, user reviews)
2. **YAML profiles** in `config/profiles/` (gitignored, one per file)
3. **Adapter pattern** for per-ATS fillers (same as scrapers)
4. **Separate `applications` table** for tracking (not reusing jobs table)
5. **`wait_for_selector`** for all navigation (not `query_selector` — SPA pages need time to render)
6. **`networkidle`** for page.goto (not `domcontentloaded` — Workday is JS-heavy)
7. **ATS account creation handled by filler** (not deferred — it's required for Workday)

### Open
1. **Multi-page wizard navigation**: Human-driven vs auto-driven? Recommend human-driven for v2.
2. **Custom dropdowns/radios**: Fill what we can, skip what we can't? Or build dropdown handlers?
3. **Handling UNSUPPORTED_ATS at scale**: Generic filler vs per-ATS fillers vs LLM-assisted? Needs decision after Workday works.

---

## Acceptance Criteria for v2

v2 is **done** when:
1. `apply --next --company nasdaq` opens browser, creates account (or signs in), fills My Information page with Given Name and Family Name
2. User can navigate the wizard pages in the browser, filler fills text fields on each page
3. Resume is uploaded on My Experience page
4. User confirms submission on Review page via terminal
5. Application is recorded in database with SUBMITTED status
6. At least 1 real Nasdaq application is submitted successfully end-to-end
7. All unit tests pass (242+)

---

## Files Reference

### Core applier
- `src/applier/base.py` — BaseFormFiller ABC, FillResult
- `src/applier/registry.py` — Filler registry, get_filler_for_url
- `src/applier/orchestrator.py` — ApplyOrchestrator, Playwright session
- `src/applier/workday.py` — Workday filler (navigation + form fill)
- `src/applier/oracle_hcm.py` — Oracle HCM filler
- `src/applier/url_resolver.py` — Apply URL resolver (built, not integrated)

### Models and persistence
- `src/models/user_profile.py` — UserProfile dataclass, YAML loader
- `src/persistence/repository.py` — ApplicationRepository
- `src/persistence/database.py` — Schema with applications tables

### Config
- `config/profiles/example.yaml` — Template (committed)
- `config/profiles/backend_mumbai.yaml` — Real profile (gitignored)

### Tests
- `tests/unit/test_workday_filler.py` — 25 tests
- `tests/unit/test_oracle_hcm_filler.py` — 19 tests
- `tests/unit/test_user_profile.py` — 22 tests
- `tests/unit/test_application_repository.py` — 24 tests
- `tests/unit/test_apply_orchestrator.py` — 11 tests
- `tests/unit/test_filler_registry.py` — 11 tests
