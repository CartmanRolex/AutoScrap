# AutoScrap — Swiss Car Listing Scraper

## Goal
Scrape new listings from https://www.autoscout24.ch/fr/s every 2 minutes
and store them incrementally in a local SQLite database.

## Stack
- Python 3.13 + patchright (patched Playwright fork for Cloudflare bypass)
- sqlite3 (stdlib) for the database

## Phases
- Phase 1 (discover.py): stealth browser navigates the site, intercepts all XHR/Fetch
  JSON responses, dumps to data/api_discovery.jsonl + data/trace.har
- Phase 2 (main.py): calls the discovered API endpoint inside the same browser session
  (keeps CF cookies alive), polls every 120s, upserts new listings into autoscrap.db

## Dev Workflow
1. Activate venv: `.venv\Scripts\activate`
2. After every meaningful change: git add → git commit → git push
3. Never commit: .venv/, data/*.db, data/*.jsonl, data/*.har

## Git Remote
git@github-autoscrap:CartmanRolex/AutoScrap.git
