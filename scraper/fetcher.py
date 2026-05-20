"""Fetch and extract listing data from AutoScout24 search results page."""
import re
import json


SEARCH_URL = "https://www.autoscout24.ch/fr/s"
SORT_PARAMS = "?sort=createdDate&dir=desc"


async def navigate_to_listings(page) -> list[dict]:
    # First navigate to the base URL to let Cloudflare establish a session,
    # then navigate to the sorted URL — direct sorted requests get CF-blocked.
    await page.goto(SEARCH_URL, wait_until="networkidle", timeout=90_000)
    await page.wait_for_timeout(3_000)
    url = SEARCH_URL + SORT_PARAMS
    await page.goto(url, wait_until="networkidle", timeout=90_000)
    await page.wait_for_timeout(3_000)
    html = await page.content()
    return extract_listings_from_html(html)


async def reload_listings(page) -> list[dict]:
    """Reload within the same browser session (keeps CF cookies alive)."""
    await page.reload(wait_until="networkidle", timeout=90_000)
    await page.wait_for_timeout(2_000)
    html = await page.content()
    return extract_listings_from_html(html)


def extract_listings_from_html(html: str) -> list[dict]:
    """Parse the prefetchedListings blob from the Next.js streaming HTML."""
    marker = '\\"prefetchedListings\\":'
    idx = html.find(marker)
    if idx < 0:
        # Fallback: try the totalElements anchor
        m = re.search(r'\\"totalElements\\":\d+,\\"size\\":\d+', html)
        if not m:
            return []
        idx = m.start()
        # Walk back to find the opening { of the pagination object
        for i in range(idx, max(0, idx - 500), -1):
            if html[i] == '{':
                idx = i
                break
    else:
        idx = idx + len(marker)
        # Skip whitespace to land on {
        while idx < len(html) and html[idx] in ' \t\n\r':
            idx += 1

    if html[idx] != '{':
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
    # Unescape the Next.js double-encoded JSON string
    raw = escaped.replace('\\"', '"').replace('\\\\', '\\')
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    return data.get("content", [])
