# Run Commands

All commands should be run from the project root (`/Users/srinivasravi/dev/JobSearchAutomater`).

**IMPORTANT**: Always activate the virtual environment first before running any command:

```bash
source .venv/bin/activate
```

## First-time Setup

```bash
# Create virtual environment (one-time)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (one-time, needed for Goldman Sachs, Google, BofA, Microsoft scrapers)
python3 -m playwright install chromium
```

## Scraping

```bash
# Scrape all enabled sources (Mumbai profile, default)
python3 -m src.cli scrape

# Scrape a specific source
python3 -m src.cli scrape --source amazon
python3 -m src.cli scrape --source jpmorgan
python3 -m src.cli scrape --source google

# Scrape using Pune profile
python3 -m src.cli scrape --profile pune

# Scrape a single source in Pune
python3 -m src.cli scrape --profile pune --source barclays
```

### Available sources (Mumbai)
| Source | Company | Type | Status |
|--------|---------|------|--------|
| amazon | Amazon | HTTP (JSON API) | Working |
| barclays | Barclays | HTTP (HTML) | Working |
| citi | Citi | HTTP (HTML) | Working |
| nomura | Nomura | HTTP (HTML) | Working |
| visa | Visa | HTTP (JSON API) | Working |
| msci | MSCI | HTTP (Algolia) | Working |
| morningstar | Morningstar | HTTP (Phenom JS) | Working |
| jpmorgan | JPMorganChase | HTTP (Oracle HCM API) | Working |
| nasdaq | Nasdaq | HTTP (Workday API) | Working |
| oracle | Oracle | HTTP (Oracle HCM API) | Working |
| goldman_sachs | Goldman Sachs | Playwright | Working |
| google | Google | Playwright | Working |
| bofa | Bank of America | Playwright | Working |
| microsoft | Microsoft | Playwright | Working |
| morgan_stanley | Morgan Stanley | Disabled (reCAPTCHA) | |
| deutsche_bank | Deutsche Bank | Disabled (wrong country) | |
| ubs | UBS | Disabled (login required) | |
| bnp_paribas | BNP Paribas | Disabled (WAF 403) | |
| sp_global | S&P Global | Disabled (hCaptcha) | |

## Querying

```bash
# View job stats (count by company, source, status)
python3 -m src.cli stats

# Browse jobs (most recent first)
python3 -m src.cli query

# Filter by company
python3 -m src.cli query --company Google

# Filter by source
python3 -m src.cli query --source jpmorgan

# Limit results
python3 -m src.cli query --limit 5

# JSON output
python3 -m src.cli query --json
```

## Export

```bash
# Export all jobs to CSV (stdout)
python3 -m src.cli export

# Export to file
python3 -m src.cli export --output jobs.csv
```

## History

```bash
# View recent scrape runs
python3 -m src.cli runs

# List available scraping profiles
python3 -m src.cli profiles
```

---

## Applying to Jobs (v2)

### Setup

Create your user profile (contains your personal info for form filling):

```bash
# Copy the example template and fill in your details
cp config/profiles/example.yaml config/profiles/backend_mumbai.yaml
# Edit the file with your name, email, phone, resume path, etc.
```

Your profile YAML is gitignored — it stays local and never gets committed.

### List profiles and apply queue

```bash
# See available user profiles
python3 -m src.cli list-profiles

# Show jobs in the apply queue (NOT_APPLIED, no application attempt yet)
python3 -m src.cli apply-queue
python3 -m src.cli apply-queue --limit 50
```

### Apply to jobs

This opens a **visible Chromium browser**, fills the form, then pauses for your review.

```bash
# Apply to the next pending job (uses first available profile)
python3 -m src.cli apply --next

# Apply to next 5 jobs
python3 -m src.cli apply --next --limit 5

# Apply to a specific job by ID
python3 -m src.cli apply --job-id 42

# Use a specific profile
python3 -m src.cli apply --next --profile backend_mumbai
python3 -m src.cli apply --job-id 42 --profile ai_remote
```

When the form is filled, the terminal will show:
```
--- Form Filled ---
Job:     Backend Engineer @ Acme Corp
Filled:  first_name, last_name, email, phone
Skipped: resume

Submit? [y/n/skip]:
```
- `y` — clicks Submit, records SUBMITTED
- `n` — closes browser, records FAILED (HUMAN_REJECTED)
- `skip` — closes browser, no status change

### View application history and stats

```bash
# Application statistics (by status, profile, method)
python3 -m src.cli apply-stats

# List all applications
python3 -m src.cli applications

# Filter by status
python3 -m src.cli applications --status SUBMITTED
python3 -m src.cli applications --status FAILED

# Filter by profile
python3 -m src.cli applications --profile backend_mumbai
```

### Mark a job as manually applied

```bash
python3 -m src.cli mark-applied --job-id 42
python3 -m src.cli mark-applied --job-id 42 --profile backend_mumbai
```

### Supported ATS platforms

| Platform | URLs | Jobs in DB |
|----------|------|-----------|
| Oracle HCM | `*.taleo.net`, `*.oraclecloud.com` | ~625 (JPMorgan, Oracle) |
| Workday | `*.myworkdayjobs.com`, `*.workday.com` | ~25+ (Nasdaq + others) |

Jobs on unsupported platforms are recorded as FAILED with reason `UNSUPPORTED_ATS`.

## Testing

```bash
# Run all unit tests
python3 -m pytest tests/unit/ -v

# Run tests for a specific adapter
python3 -m pytest tests/unit/test_jpmorgan_scraper.py -v

# Run with coverage
python3 -m pytest tests/unit/ --cov=src --cov-report=term-missing
```

## Database

The SQLite database is stored at `data/jobs.db` by default. You can override it:

```bash
python3 -m src.cli scrape --db data/custom.db
python3 -m src.cli stats --db data/custom.db
```

To reset the database, just delete the file:
```bash
rm data/jobs.db
```
