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

# List available profiles
python3 -m src.cli profiles
```

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
