from contextlib import asynccontextmanager
from typing import AsyncGenerator

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.config import settings
from app.models.settings import CookieEntry


class BrowserFactory:
    """Creates and manages Playwright browser instances."""

    @asynccontextmanager
    async def create_context(
        self,
        cookies: list[CookieEntry] | None = None,
    ) -> AsyncGenerator[BrowserContext, None]:
        async with async_playwright() as playwright:
            browser: Browser = await playwright.chromium.launch(
                headless=settings.browser_headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--lang=ja-JP",
                ],
            )
            try:
                context: BrowserContext = await browser.new_context(
                    locale="ja-JP",
                    timezone_id="Asia/Tokyo",
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 800},
                )

                if cookies:
                    await context.add_cookies(
                        [self._to_playwright_cookie(c) for c in cookies]
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
        async with self.create_context(cookies) as context:
            page: Page = await context.new_page()
            page.set_default_timeout(settings.browser_timeout_ms)
            try:
                yield page
            finally:
                await page.close()

    @staticmethod
    def _to_playwright_cookie(cookie: CookieEntry) -> dict:
        result: dict = {
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
