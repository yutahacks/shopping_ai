"""Browser lifecycle management using Playwright.

Provides a factory for creating and configuring headless Chromium browser
instances with Japanese locale settings and optional cookie injection.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.config import settings
from app.models.settings import CookieEntry

# Realistic, up-to-date User-Agent to avoid bot detection by Amazon.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class BrowserFactory:
    """Creates and manages Playwright browser instances."""

    @asynccontextmanager
    async def create_context(
        self,
        cookies: list[CookieEntry] | None = None,
    ) -> AsyncGenerator[BrowserContext, None]:
        """Creates a browser context with Japanese locale settings.

        Args:
            cookies: Optional cookies to inject into the context.

        Yields:
            A configured BrowserContext instance.
        """
        async with async_playwright() as playwright:
            launch_args = [
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--lang=ja-JP",
            ]
            # Only disable sandbox in headless/container mode
            if settings.browser_headless:
                launch_args.extend(["--no-sandbox", "--disable-setuid-sandbox"])

            browser: Browser = await playwright.chromium.launch(
                headless=settings.browser_headless,
                args=launch_args,
            )
            try:
                context: BrowserContext = await browser.new_context(
                    locale="ja-JP",
                    timezone_id="Asia/Tokyo",
                    user_agent=_USER_AGENT,
                    viewport={"width": 1280, "height": 800},
                )
                # Hide navigator.webdriver to evade bot detection
                await context.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )

                if cookies:
                    await context.add_cookies(
                        [self._to_playwright_cookie(c) for c in cookies]  # type: ignore[misc]
                    )

                try:
                    yield context
                finally:
                    await context.close()
            finally:
                await browser.close()

    @asynccontextmanager
    async def create_page(
        self,
        cookies: list[CookieEntry] | None = None,
    ) -> AsyncGenerator[Page, None]:
        """Creates a single browser page with default timeout.

        Args:
            cookies: Optional cookies to inject into the browser context.

        Yields:
            A configured Page instance.
        """
        async with self.create_context(cookies) as context:
            page: Page = await context.new_page()
            page.set_default_timeout(settings.browser_timeout_ms)
            try:
                yield page
            finally:
                await page.close()

    @staticmethod
    def _to_playwright_cookie(cookie: CookieEntry) -> dict[str, object]:
        result: dict[str, object] = {
            "name": cookie.name,
            "value": cookie.value,
            "domain": cookie.domain,
            "path": cookie.path,
            "secure": cookie.secure,
            "httpOnly": cookie.http_only,
        }
        if cookie.same_site:
            result["sameSite"] = cookie.same_site
        if cookie.expires is not None:
            result["expires"] = cookie.expires
        return result
