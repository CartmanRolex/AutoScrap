# AutoScrap

Incremental scraper for Swiss used-car listings. Polls **AutoScout24.ch** and **anibis.ch**
every 2 minutes and stores new listings in a local SQLite database (`autoscrap.db`),
deduplicated by listing ID.

## How it works

- **AutoScout24**: a stealth browser session (patchright, a patched Playwright fork) passes the
  Cloudflare challenge once, then reloads the "newest first" results page and extracts listings
  from the embedded JSON-LD block.
- **anibis.ch**: fetched over plain HTTP; detail pages are only requested for IDs not yet in the DB.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
patchright install chromium
```

## Usage

```bash
python main.py            # start polling both sources
python export_json.py     # dump the database to JSON
```

`discover.py` is the one-off exploration script used to reverse-engineer the AutoScout24 page
(findings documented in `CLAUDE.md`); `verify_*.py` are manual smoke tests.

## Structure

- `scraper/` — browser handling, fetchers, and parsers per source
- `db/` — SQLite schema and upsert/dedup repository
- `notebooks/` — ad-hoc analysis of collected data
- `data/` — scraped artifacts (gitignored)
