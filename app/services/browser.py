import logging

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.config import Settings, get_settings
from app.utils.proxy import proxy_rotator


logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


class BrowserFetchError(RuntimeError):
    """Raised when the remote browser cannot fetch a page."""


async def fetch_html(url: str) -> str:
    """Fetch rendered HTML using a remote Playwright browser server.

    The API container connects to a separate Playwright Docker service. This
    keeps browser memory/CPU spikes isolated from the FastAPI process and lets
    the browser layer scale independently later.

    A randomly selected proxy is tried first; on failure the request is retried
    with the next proxy in the rotation, finally falling back to a direct
    connection. ``BrowserFetchError`` is raised only when every attempt fails.
    """

    settings = get_settings()
    last_error: BrowserFetchError | None = None

    for proxy in proxy_rotator.selection():
        try:
            return await _fetch_once(url, proxy, settings)
        except PlaywrightTimeoutError as exc:
            logger.warning("Timeout fetching %s (proxy=%s)", url, bool(proxy))
            last_error = BrowserFetchError("Timed out while fetching the URL.")
        except Exception as exc:  # noqa: BLE001 - browser/proxy errors are diverse
            logger.warning(
                "Fetch attempt failed for %s (proxy=%s): %s", url, bool(proxy), exc
            )
            last_error = BrowserFetchError(
                "Unable to fetch URL with browser service."
            )

    raise last_error or BrowserFetchError("Unable to fetch URL with browser service.")


async def _fetch_once(url: str, proxy: str | None, settings: Settings) -> str:
    """Run a single fetch attempt against the remote browser with one proxy."""

    context_options: dict[str, object] = {"user_agent": _USER_AGENT}
    if proxy:
        context_options["proxy"] = {"server": proxy}

    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect(settings.playwright_server_url)
        try:
            context = await browser.new_context(**context_options)
            page = await context.new_page()
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=settings.browser_timeout_ms,
            )
            html = await page.content()
            await context.close()
            return html
        finally:
            await browser.close()
