"""HTTP fetch helpers for Anibis."""
import asyncio

import httpx

from scraper.anibis_parser import extract_detail_listing, extract_search_nodes

SEARCH_URL = "https://www.anibis.ch/fr/q/voitures/Ak8CkY2Fyc5TAwMDA"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-CH,fr;q=0.9,en;q=0.7",
}


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers=_HEADERS,
        follow_redirects=True,
        timeout=httpx.Timeout(30.0),
    )


async def _get_text(client: httpx.AsyncClient, url: str, attempts: int = 3) -> str:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            await asyncio.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}") from last_error


async def fetch_search_nodes(
    client: httpx.AsyncClient, page: int = 1, sorting: str = "newest"
) -> list[dict]:
    html = await _get_text(client, f"{SEARCH_URL}?sorting={sorting}&page={page}")
    return extract_search_nodes(html)


async def fetch_detail_listing(client: httpx.AsyncClient, url: str) -> dict:
    html = await _get_text(client, url, attempts=3)
    return extract_detail_listing(html)
