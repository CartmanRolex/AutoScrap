"""Fetch and extract listing data from AutoScout24 search results page."""
import re
import json
import asyncio


SEARCH_URL = "https://www.autoscout24.ch/fr/s"
SORT_PARAMS = "?sort=createdDate&dir=desc"
_MARKER = '\\"prefetchedListings\\":'

# How long (seconds) to wait for the human to pass the CF challenge
CF_CHALLENGE_TIMEOUT_S = 180


async def _wait_for_listings(page, timeout_s: int = CF_CHALLENGE_TIMEOUT_S) -> str:
    """Poll page HTML every 2 s until the listings blob appears or timeout."""
    print(f"Waiting for listings page (up to {timeout_s}s) — complete the Cloudflare check if prompted ...")
    for _ in range(timeout_s // 2):
        html = await page.content()
        if _MARKER in html:
            return html
        await asyncio.sleep(2)
    raise TimeoutError(f"Listings not found after {timeout_s}s — CF challenge not completed?")


async def navigate_to_listings(page) -> list[dict]:
    """Navigate to the sorted listings page, waiting for the human CF check."""
    url = SEARCH_URL + SORT_PARAMS
    await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    html = await _wait_for_listings(page)
    return extract_listings_from_html(html)


async def reload_listings(page) -> list[dict]:
    """Reload within the same session (CF cookies stay alive, no re-challenge)."""
    await page.goto(SEARCH_URL + SORT_PARAMS, wait_until="domcontentloaded", timeout=60_000)
    html = await _wait_for_listings(page, timeout_s=30)
    return extract_listings_from_html(html)


def extract_listings_from_html(html: str) -> list[dict]:
    """Parse the prefetchedListings blob from the Next.js streaming HTML."""
    idx = html.find(_MARKER)
    if idx < 0:
        return []

    idx += len(_MARKER)
    while idx < len(html) and html[idx] in ' \t\n\r':
        idx += 1

    if idx >= len(html) or html[idx] != '{':
        return []

    # Walk braces to find the closing }
    depth = 0
    end = idx
    for i in range(idx, min(len(html), idx + 5_000_000)):
        c = html[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    escaped = html[idx:end]
    raw = escaped.replace('\\"', '"').replace('\\\\', '\\')
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    return data.get("content", [])
