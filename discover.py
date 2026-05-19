"""Phase 1 — navigate to AutoScout24, bypass Cloudflare, intercept listing API calls."""
import asyncio

from scraper.browser import launch_browser
from scraper.interceptor import attach_interceptor

TARGET = "https://www.autoscout24.ch/fr/s"


async def main() -> None:
    print(f"Launching browser and navigating to {TARGET} ...")
    p, browser, context = await launch_browser(headless=False)
    page = await context.new_page()
    await attach_interceptor(page)

    await page.goto(TARGET, wait_until="networkidle", timeout=60_000)
    print("Page loaded. Waiting for lazy XHR requests ...")
    await page.wait_for_timeout(8_000)

    await context.close()
    await browser.close()
    await p.stop()
    print("Done.")
    print("  → data/api_discovery.jsonl  (all JSON responses)")
    print("  → data/trace.har            (full HAR for DevTools import)")


asyncio.run(main())
