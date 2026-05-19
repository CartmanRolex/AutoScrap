from patchright.async_api import async_playwright


async def launch_browser(headless: bool = False):
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=headless)
    context = await browser.new_context(
        viewport={"width": 1366, "height": 768},
        locale="fr-CH",
        timezone_id="Europe/Zurich",
        record_har_path="data/trace.har",
        record_har_url_filter="*autoscout24*",
    )
    return p, browser, context
