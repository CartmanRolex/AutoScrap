from patchright.async_api import async_playwright

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


async def launch_browser(headless: bool = False):
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=headless)
    context = await browser.new_context(
        viewport={"width": 1366, "height": 768},
        locale="fr-CH",
        timezone_id="Europe/Zurich",
        user_agent=_UA,
    )
    return p, browser, context
