"""Service for managing Amazon session cookies.

Provides storage, validation, and lifecycle management for browser
cookies used to authenticate with Amazon Fresh.
"""

import asyncio
import json
import logging
import os
import stat
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings
from app.models.settings import CookieEntry, CookieStatus

logger = logging.getLogger(__name__)

AMAZON_LOGIN_URL = "https://www.amazon.co.jp/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.co.jp%2F&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=jpflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"
AMAZON_TOP_URL = "https://www.amazon.co.jp/"
LOGIN_TIMEOUT_SEC = 180


class CookieManagerService:
    """Manages Amazon session cookies stored as a JSON file.

    Attributes:
        _path: Path to the cookies JSON file.
        _lock: Async lock for thread-safe file access.
    """

    def __init__(self, cookies_path: Path | None = None) -> None:
        """Initializes the cookie manager.

        Args:
            cookies_path: Optional path to the cookies JSON file.
                Falls back to the configured default path.
        """
        self._path = cookies_path or settings.cookies_path
        self._lock = asyncio.Lock()

    async def get_status(self) -> CookieStatus:
        """Returns the current cookie status including validity.

        Returns:
            Cookie status with count, validity, and last updated time.
        """
        async with self._lock:
            return await asyncio.to_thread(self._check_status)

    async def save_cookies(self, cookies: list[CookieEntry]) -> CookieStatus:
        """Saves cookies to disk and returns the updated status.

        Args:
            cookies: List of cookie entries to persist.

        Returns:
            The cookie status after saving.
        """
        async with self._lock:
            await asyncio.to_thread(self._write_cookies, cookies)
        logger.info("Saved %d cookies to %s", len(cookies), self._path)
        return await self.get_status()

    async def delete_cookies(self) -> None:
        """Deletes the stored cookies file from disk."""
        async with self._lock:
            await asyncio.to_thread(self._delete_cookies)
        logger.info("Deleted cookies file at %s", self._path)

    async def load_cookies(self) -> list[CookieEntry]:
        """Loads and returns all stored cookies.

        Returns:
            List of cookie entries, or an empty list if none exist.
        """
        async with self._lock:
            cookies = await asyncio.to_thread(self._read_cookies)
        logger.debug("Loaded %d cookies from %s", len(cookies), self._path)
        return cookies

    def _check_status(self) -> CookieStatus:
        if not self._path.exists():
            return CookieStatus(has_cookies=False, message="Cookieが設定されていません")

        cookies = self._read_cookies()
        if not cookies:
            return CookieStatus(has_cookies=False, message="Cookieファイルが空です")

        now = datetime.now(UTC).timestamp()
        valid_cookies = [c for c in cookies if c.expires is None or c.expires > now]

        file_stat = self._path.stat()
        last_updated = datetime.fromtimestamp(file_stat.st_mtime, tz=UTC).isoformat()

        is_valid = len(valid_cookies) > 0
        return CookieStatus(
            has_cookies=True,
            cookie_count=len(cookies),
            is_valid=is_valid,
            last_updated=last_updated,
            message="有効なCookieがあります" if is_valid else "Cookieが期限切れです",
        )

    def _read_cookies(self) -> list[CookieEntry]:
        if not self._path.exists():
            return []
        with open(self._path, encoding="utf-8") as f:
            data = json.load(f)
        return [CookieEntry.model_validate(c) for c in data]

    def _write_cookies(self, cookies: list[CookieEntry]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [c.model_dump(exclude_none=True) for c in cookies]
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # Restrict file permissions to owner only (sensitive data)
        os.chmod(self._path, stat.S_IRUSR | stat.S_IWUSR)

    def _delete_cookies(self) -> None:
        if self._path.exists():
            self._path.unlink()

    async def browser_login(self) -> CookieStatus:
        """Launch a headed browser for the user to log in to Amazon.

        Opens a visible Chromium browser, navigates to the Amazon login page,
        and waits for the user to complete login (including 2FA/CAPTCHA).
        Once logged in, captures all cookies and saves them.

        Returns:
            Cookie status after saving the captured cookies.

        Raises:
            TimeoutError: If login is not completed within the timeout period.
            RuntimeError: If the browser cannot be launched.
        """
        from playwright.async_api import async_playwright

        logger.info("Starting browser login flow (timeout: %ds)", LOGIN_TIMEOUT_SEC)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=False,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--lang=ja-JP"],
            )
            try:
                context = await browser.new_context(
                    locale="ja-JP",
                    timezone_id="Asia/Tokyo",
                    viewport={"width": 1280, "height": 800},
                )
                page = await context.new_page()

                # Navigate to Amazon login page
                await page.goto(AMAZON_LOGIN_URL, wait_until="domcontentloaded")
                logger.info("Opened Amazon login page, waiting for user to log in...")

                # Wait until the user completes login and lands on Amazon top
                # Login is detected when the URL no longer contains '/ap/signin'
                # and the nav shows an account name (not "ログイン")
                try:
                    await page.wait_for_url(
                        lambda url: "/ap/signin" not in url and "/ap/mfa" not in url,
                        timeout=LOGIN_TIMEOUT_SEC * 1000,
                    )
                except Exception:
                    raise TimeoutError(
                        f"ログインが{LOGIN_TIMEOUT_SEC}秒以内に完了しませんでした。"
                        "もう一度お試しください。"
                    )

                # Give a moment for cookies to settle after redirect
                await page.wait_for_timeout(2000)

                # Verify login by checking the account nav text
                try:
                    nav_text = await page.text_content("#nav-link-accountList", timeout=5000)
                    if nav_text and "ログイン" in nav_text:
                        raise RuntimeError(
                            "ログインが完了していないようです。もう一度お試しください。"
                        )
                except Exception as e:
                    if isinstance(e, RuntimeError):
                        raise
                    # If we can't check the nav, proceed anyway — cookies might still be valid
                    logger.warning("Could not verify login status via nav: %s", e)

                # Capture all cookies from the browser context
                raw_cookies = await context.cookies()
                logger.info("Captured %d cookies from browser", len(raw_cookies))

                # Convert to our CookieEntry model
                entries = [
                    CookieEntry(
                        name=c["name"],
                        value=c["value"],
                        domain=c["domain"],
                        path=c.get("path", "/"),
                        secure=c.get("secure", False),
                        http_only=c.get("httpOnly", False),
                        same_site=c.get("sameSite"),
                        expires=c.get("expires"),
                    )
                    for c in raw_cookies
                    if ".amazon.co.jp" in c["domain"] or "amazon.co.jp" == c["domain"]
                ]

                if not entries:
                    raise RuntimeError(
                        "Amazon関連のCookieが取得できませんでした。"
                        "ログインが正しく完了したか確認してください。"
                    )

                logger.info(
                    "Filtered %d Amazon cookies (from %d total)",
                    len(entries),
                    len(raw_cookies),
                )

            finally:
                await browser.close()

        return await self.save_cookies(entries)
