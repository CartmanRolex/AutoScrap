"""Fetch and extract listing data from AutoScout24 search results page."""
import re
import json
import asyncio


SEARCH_URL = "https://www.autoscout24.ch/fr/s"
SORT_URL = SEARCH_URL + "?sort%5B0%5D%5Btype%5D=CREATED_DATE&sort%5B0%5D%5Border%5D=DESC"
_MARKER = '\\"prefetchedListings\\":'


async def _human_mouse(page) -> None:
    """Simulate natural mouse movement across the page before interacting."""
    moves = [(150, 400), (300, 300), (500, 350), (400, 250), (600, 420)]
    for x, y in moves:
        await page.mouse.move(x, y)
        await asyncio.sleep(0.15)
    await page.evaluate("window.scrollBy(0, 120)")
    await asyncio.sleep(0.4)
    await page.evaluate("window.scrollBy(0, -40)")
    await asyncio.sleep(0.3)


async def _auto_pass_cf(page, timeout_s: int = 90) -> None:
    """Detect CF Turnstile and auto-click through it with realistic mouse behaviour."""
    # Give the managed JS challenge time to auto-resolve first
    await asyncio.sleep(4)
    await _human_mouse(page)

    for attempt in range(timeout_s // 3):
        html = await page.content()
        if _MARKER in html:
            return  # on the real listings page

        clicked = False
        iframe_loc = page.locator('iframe[src*="challenges.cloudflare.com"]')
        if await iframe_loc.count() > 0:
            box = await iframe_loc.bounding_box()
            if box:
                # Aim for the checkbox which sits ~22px from the left edge of the iframe
                tx = box["x"] + 22
                ty = box["y"] + box["height"] / 2
                # Approach from a natural position
                await page.mouse.move(tx - 120, ty - 40)
                await asyncio.sleep(0.25)
                await page.mouse.move(tx - 40, ty - 10)
                await asyncio.sleep(0.15)
                await page.mouse.click(tx, ty)
                print(f"Auto-clicked CF Turnstile at ({tx:.0f}, {ty:.0f}), waiting ...")
                clicked = True
                await asyncio.sleep(6)

        if not clicked:
            # Fallback: try clicking inside the frame directly
            for frame in page.frames:
                if "challenges.cloudflare.com" in frame.url:
                    for sel in ('input[type="checkbox"]', "button"):
                        try:
                            el = frame.locator(sel).first
                            if await el.count() > 0:
                                await el.click(timeout=1_000)
                                print(f"Auto-clicked CF element via frame ({sel})")
                                await asyncio.sleep(6)
                                break
                        except Exception:
                            pass
                    break

        await asyncio.sleep(3)

    raise TimeoutError(f"CF challenge not resolved after {timeout_s}s")


async def navigate_to_listings(page) -> list[dict]:
    """First load: navigate to sorted URL and pass CF challenge."""
    await page.goto(SORT_URL, wait_until="domcontentloaded", timeout=60_000)
    await _auto_pass_cf(page)
    html = await page.content()
    return extract_listings_from_html(html)


async def reload_listings(page) -> list[dict]:
    """Subsequent polls: navigate to sorted URL (CF cookies stay alive)."""
    await page.goto(SORT_URL, wait_until="domcontentloaded", timeout=60_000)
    await _auto_pass_cf(page, timeout_s=30)
    html = await page.content()
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
