"""One-off: verify that ?sort=createdDate&desc=true actually sorts newest first."""
import asyncio
from scraper.browser import launch_browser
from scraper.fetcher import navigate_to_listings
from scraper.parser import parse_listing


async def main():
    p, browser, context = await launch_browser(headless=False)
    page = await context.new_page()
    print("Complete the Cloudflare challenge if it appears ...")
    raw = await navigate_to_listings(page)
    await context.close(); await browser.close(); await p.stop()

    if not raw:
        print("ERROR: no listings")
        return

    print(f"Got {len(raw)} listings sorted by createdDate desc:")
    for r in raw[:5]:
        l = parse_listing(r)
        print(f"  {l['as24_created_at'][:19]}  {l['id']}  {l['version_full_name'][:50]}")


asyncio.run(main())
