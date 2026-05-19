"""Phase 1 — navigate to AutoScout24, bypass Cloudflare, intercept listing API calls."""
import asyncio
import json
import pathlib

from scraper.browser import launch_browser
from scraper.interceptor import attach_interceptor

TARGET = "https://www.autoscout24.ch/fr/s"
NEXT_DATA_PATH = pathlib.Path("data/next_data.json")
HTML_DUMP_PATH = pathlib.Path("data/page_dump.html")


async def main() -> None:
    print(f"Launching browser and navigating to {TARGET} ...")
    p, browser, context = await launch_browser(headless=False)
    page = await context.new_page()
    await attach_interceptor(page)

    await page.goto(TARGET, wait_until="networkidle", timeout=90_000)
    print("Page loaded. Waiting for lazy XHR requests ...")
    await page.wait_for_timeout(10_000)

    # Dump raw HTML for inspection
    html = await page.content()
    HTML_DUMP_PATH.write_text(html, encoding="utf-8")
    print(f"HTML saved ({len(html):,} bytes)")

    # Extract __NEXT_DATA__ embedded JSON (SSR data blob)
    next_data = await page.evaluate(
        "() => { const el = document.getElementById('__NEXT_DATA__'); return el ? el.textContent : null; }"
    )
    if next_data:
        parsed = json.loads(next_data)
        NEXT_DATA_PATH.write_text(
            json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"__NEXT_DATA__ saved ({len(next_data):,} chars) -> {NEXT_DATA_PATH}")
    else:
        print("No __NEXT_DATA__ found — page may still be on CF challenge or fully client-side")

    await context.close()
    await browser.close()
    await p.stop()
    print("Done.")
    print("  -> data/api_discovery.jsonl  (XHR JSON responses)")
    print("  -> data/next_data.json       (__NEXT_DATA__ SSR blob)")
    print("  -> data/page_dump.html       (raw page HTML)")


asyncio.run(main())
