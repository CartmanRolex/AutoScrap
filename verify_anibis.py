"""One-off smoke test for Anibis search + detail extraction."""
import asyncio

from scraper.anibis_fetcher import fetch_detail_listing, fetch_search_nodes, make_client
from scraper.anibis_parser import detail_url, parse_anibis_listing


async def main() -> None:
    async with make_client() as client:
        nodes = await fetch_search_nodes(client)
        print(f"Got {len(nodes)} Anibis search listings")
        for node in nodes[:5]:
            detail = await fetch_detail_listing(client, detail_url(node))
            listing = parse_anibis_listing(node, detail)
            print(
                f"  {(listing.get('as24_created_at') or '')[:19]}  "
                f"{listing['id']}  "
                f"{listing.get('make_name') or '?'} {listing.get('model_name') or '?'}  "
                f"{listing.get('price_chf') or 0} CHF"
            )


asyncio.run(main())
