"""Incremental listing poller for Swiss car marketplaces."""
import argparse
import asyncio
import logging
from datetime import datetime, timezone

from db.repository import count_listings, listing_exists, touch_listing, upsert_listing
from db.schema import init_db
from scraper.anibis_fetcher import fetch_detail_listing, fetch_search_nodes, make_client
from scraper.anibis_parser import anibis_db_id, detail_url, parse_anibis_listing
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
logging.getLogger("httpx").setLevel(logging.WARNING)


async def poll_autoscout_once(page, conn) -> tuple[int, int]:
    """Fetch one AutoScout24 page, upsert all. Returns (new, total_seen)."""
    raw_listings = await reload_listings(page)
    if not raw_listings:
        log.warning("AutoScout24: no listings extracted - possible CF challenge or page change")
        return 0, 0

    new_count = 0
    for raw in raw_listings:
        listing = parse_listing(raw)
        changed = upsert_listing(conn, listing)
        if changed:
            new_count += 1
            log.info(
                "NEW  %s | %s | %d CHF | %s",
                listing["id"],
                listing.get("version_full_name", "?"),
                listing.get("price_chf") or 0,
                (listing.get("as24_created_at") or "")[:10],
            )

    return new_count, len(raw_listings)


async def poll_anibis_once(conn, client) -> tuple[int, int]:
    """Fetch newest Anibis listings and detail pages only for new IDs."""
    search_nodes = await fetch_search_nodes(client)
    if not search_nodes:
        log.warning("Anibis: no listings extracted - page structure may have changed")
        return 0, 0

    new_count = 0
    for node in search_nodes:
        listing_id = anibis_db_id(node)
        if listing_exists(conn, listing_id):
            touch_listing(conn, listing_id)
            continue

        url = detail_url(node)
        try:
            detail_node = await fetch_detail_listing(client, url)
        except Exception as exc:
            log.warning("Anibis: detail fetch failed for %s: %s", listing_id, exc)
            continue

        listing = parse_anibis_listing(node, detail_node)
        changed = upsert_listing(conn, listing)
        if changed:
            new_count += 1
            log.info(
                "NEW  %s | %s | %d CHF | %s",
                listing["id"],
                listing.get("version_full_name", "?"),
                listing.get("price_chf") or 0,
                (listing.get("as24_created_at") or "")[:10],
            )

        await asyncio.sleep(0.15)

    return new_count, len(search_nodes)


async def main(run_once: bool = False) -> None:
    log.info("Initialising database ...")
    conn = init_db()
    log.info(
        "Existing listings in DB: %d (%d AutoScout24, %d Anibis)",
        count_listings(conn),
        count_listings(conn, "autoscout24"),
        count_listings(conn, "anibis"),
    )

    log.info("Launching browser ...")
    p, browser, context = await launch_browser(headless=False)
    page = await context.new_page()
    anibis_client = make_client()

    try:
        log.info(
            "Loading AutoScout24 page - if a Cloudflare challenge appears, "
            "click through it in the browser window."
        )
        raw_listings = await navigate_to_listings(page)
        if not raw_listings:
            log.error("First AutoScout24 fetch returned no listings - CF challenge not completed?")
            return

        new_autoscout = 0
        for raw in raw_listings:
            if upsert_listing(conn, parse_listing(raw)):
                new_autoscout += 1
        log.info("Seeded AutoScout24: +%d new / %d seen", new_autoscout, len(raw_listings))

        try:
            new_anibis, seen_anibis = await poll_anibis_once(conn, anibis_client)
            log.info("Seeded Anibis: +%d new / %d seen", new_anibis, seen_anibis)
        except Exception as exc:
            log.error("Initial Anibis fetch failed: %s", exc)

        log.info(
            "DB total: %d (%d AutoScout24, %d Anibis)",
            count_listings(conn),
            count_listings(conn, "autoscout24"),
            count_listings(conn, "anibis"),
        )

        if run_once:
            log.info("Run-once requested; exiting before poll loop.")
            return

        log.info("Starting poll loop every %ds ...", POLL_INTERVAL_S)
        while True:
            await asyncio.sleep(POLL_INTERVAL_S)
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            log.info("[%s] Polling AutoScout24 + Anibis ...", ts)
            try:
                as_new, as_seen = await poll_autoscout_once(page, conn)
                anibis_new, anibis_seen = await poll_anibis_once(conn, anibis_client)
                log.info(
                    "[%s] AutoScout24 +%d/%d, Anibis +%d/%d | DB total: %d",
                    ts,
                    as_new,
                    as_seen,
                    anibis_new,
                    anibis_seen,
                    count_listings(conn),
                )
            except Exception as exc:
                log.error("Poll error: %s", exc)
    except KeyboardInterrupt:
        log.info("Stopping.")
    finally:
        await anibis_client.aclose()
        await context.close()
        await browser.close()
        await p.stop()
        log.info("Browser closed. DB has %d listings.", count_listings(conn))
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Poll AutoScout24 and Anibis listings.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run the initial AutoScout24 and Anibis scrape, then exit.",
    )
    args = parser.parse_args()
    asyncio.run(main(run_once=args.once))
