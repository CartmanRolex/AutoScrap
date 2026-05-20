"""
Click 'Ajoutés récemment' in the browser and capture the URL autoscout24 uses.
Run this once to discover the real sort URL, then check CLAUDE.md.
"""
import asyncio
from scraper.browser import launch_browser
from scraper.fetcher import _wait_for_listings, extract_listings_from_html
from scraper.parser import parse_listing


async def main():
    p, browser, context = await launch_browser(headless=False)
    page = await context.new_page()

    print("Navigating ... complete the Cloudflare check if it appears.")
    await page.goto("https://www.autoscout24.ch/fr/s", wait_until="domcontentloaded", timeout=60_000)
    await _wait_for_listings(page)
    print(f"Listings page loaded: {page.url}")

    # Find and click the sort trigger button (Chakra menu button with aria-expanded)
    trigger = page.locator('button[aria-expanded]').first
    print(f"Clicking sort trigger ...")
    await trigger.click()
    await page.wait_for_timeout(1_000)

    # Click "Ajoutés récemment"
    option = page.locator('[role="menuitemradio"]').filter(has_text="Ajout")
    await option.click()
    print("Clicked 'Ajoutés récemment', waiting for navigation ...")

    await page.wait_for_load_state("domcontentloaded", timeout=30_000)
    await page.wait_for_timeout(2_000)
    final_url = page.url
    print(f"\nFinal URL: {final_url}")

    # Verify listings are sorted correctly
    html = await page.content()
    listings = extract_listings_from_html(html)
    if listings:
        print(f"\nFirst 5 listings by createdDate:")
        for r in listings[:5]:
            l = parse_listing(r)
            print(f"  {l['as24_created_at'][:19]}  {l['id']}  {l.get('version_full_name','')[:50]}")
    else:
        print("No listings extracted after sort click.")

    await context.close(); await browser.close(); await p.stop()


asyncio.run(main())
