"""Incremental listing poller — fetches newest AutoScout24 listings every 2 minutes."""
import asyncio
import logging
from datetime import datetime, timezone

from db.schema import init_db
from db.repository import upsert_listing, count_listings
from scraper.browser import launch_browser
from scraper.fetcher import navigate_to_listings, reload_listings
from scraper.parser import parse_listing

POLL_INTERVAL_S = 120
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


async def poll_once(page, conn) -> tuple[int, int]:
    """Fetch one page of listings, upsert all. Returns (new, total_seen)."""
    raw_listings = await reload_listings(page)
    if not raw_listings:
        log.warning("No listings extracted — possible CF challenge or page change")
        return 0, 0

    new_count = 0
    for raw in raw_listings:
        listing = parse_listing(raw)
        changed = upsert_listing(conn, listing)
        if changed:
            new_count += 1
            log.info("NEW  %s | %s | %d CHF | %s",
                     listing["id"], listing.get("version_full_name", "?"),
                     listing.get("price_chf") or 0,
                     listing.get("as24_created_at", "")[:10])

    return new_count, len(raw_listings)


async def main() -> None:
    log.info("Initialising database ...")
    conn = init_db()
    log.info("Existing listings in DB: %d", count_listings(conn))

    log.info("Launching browser ...")
    p, browser, context = await launch_browser(headless=False)
    page = await context.new_page()

    log.info("Loading listings page — if a Cloudflare challenge appears, click through it in the browser window.")
    raw_listings = await navigate_to_listings(page)
    if not raw_listings:
        log.error("First fetch returned no listings — CF challenge not completed?")
        await context.close(); await browser.close(); await p.stop()
        return

    # Upsert initial batch
    for raw in raw_listings:
        upsert_listing(conn, parse_listing(raw))
    log.info("Seeded %d listings", len(raw_listings))
    log.info("DB total: %d", count_listings(conn))

    log.info("Starting poll loop every %ds ...", POLL_INTERVAL_S)
    try:
        while True:
            await asyncio.sleep(POLL_INTERVAL_S)
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            log.info("[%s] Polling ...", ts)
            try:
                new, seen = await poll_once(page, conn)
                log.info("[%s] +%d new / %d seen | DB total: %d",
                         ts, new, seen, count_listings(conn))
            except Exception as exc:
                log.error("Poll error: %s", exc)
    except KeyboardInterrupt:
        log.info("Stopping.")
    finally:
        await context.close()
        await browser.close()
        await p.stop()
        log.info("Browser closed. DB has %d listings.", count_listings(conn))


asyncio.run(main())
