"""Service for managing Amazon session cookies.

Provides storage, validation, and lifecycle management for browser
cookies used to authenticate with Amazon Fresh.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import socket
import stat
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings
from app.models.settings import CookieEntry, CookieStatus

logger = logging.getLogger(__name__)

AMAZON_LOGIN_URL = "https://www.amazon.co.jp/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.co.jp%2F&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=jpflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"
AMAZON_TOP_URL = "https://www.amazon.co.jp/"
LOGIN_TIMEOUT_SEC = 180
_CDP_STARTUP_TIMEOUT_SEC = 15

# Chromium-based browsers supported for cookie capture (in detection order).
# Only Chromium-based browsers are supported because we connect via
# Chrome DevTools Protocol (CDP), which requires a Chromium-based browser.
_CHROMIUM_BROWSERS: list[dict[str, str]] = [
    {
        "name": "Arc",
        "mac": "/Applications/Arc.app/Contents/MacOS/Arc",
    },
    {
        "name": "Google Chrome",
        "mac": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    },
    {
        "name": "Brave Browser",
        "mac": "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    },
    {
        "name": "Microsoft Edge",
        "mac": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    },
    {
        "name": "Chromium",
        "mac": "/Applications/Chromium.app/Contents/MacOS/Chromium",
    },
]


def _detect_chromium_browsers() -> list[tuple[str, str]]:
    """Detect all installed Chromium-based browsers.

    Returns:
        List of (browser_name, executable_path) tuples in priority order.

    Raises:
        RuntimeError: If no supported Chromium-based browser is found.
    """
    system = platform.system()
    key = "mac" if system == "Darwin" else None

    if key is None:
        raise RuntimeError(f"未対応のOS ({system}) です。現在macOSのみサポートしています。")

    found: list[tuple[str, str]] = []
    for browser in _CHROMIUM_BROWSERS:
        exe_path = browser.get(key, "")
        if exe_path and Path(exe_path).exists():
            logger.info("Detected browser: %s at %s", browser["name"], exe_path)
            found.append((browser["name"], exe_path))

    if not found:
        supported = ", ".join(b["name"] for b in _CHROMIUM_BROWSERS)
        raise RuntimeError(
            "対応するChromiumベースのブラウザが見つかりませんでした。"
            f"以下のいずれかをインストールしてください: {supported}"
        )

    return found


def _find_free_port() -> int:
    """Find a free TCP port for CDP debugging."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


async def _wait_for_cdp_ready(port: int) -> None:
    """Wait until the CDP endpoint is accepting connections.

    Args:
        port: The CDP debugging port to check.

    Raises:
        RuntimeError: If the CDP endpoint does not become ready in time.
    """
    deadline = time.monotonic() + _CDP_STARTUP_TIMEOUT_SEC
    while time.monotonic() < deadline:
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.close()
            await writer.wait_closed()
            return
        except OSError:
            await asyncio.sleep(0.3)
    raise RuntimeError(
        f"ブラウザのCDP接続がタイムアウトしました ({_CDP_STARTUP_TIMEOUT_SEC}秒)。"
        "ブラウザが正しく起動できなかった可能性があります。"
    )


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
        import tempfile

        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [c.model_dump(exclude_none=True) for c in cookies]

        # Atomic write: create temp file with restricted permissions, then move
        fd = tempfile.NamedTemporaryFile(
            mode="w",
            dir=self._path.parent,
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        )
        try:
            tmp_path = Path(fd.name)
            os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
            json.dump(data, fd, ensure_ascii=False, indent=2)
            fd.close()
            tmp_path.replace(self._path)
        except Exception:
            fd.close()
            Path(fd.name).unlink(missing_ok=True)
            raise

    def _delete_cookies(self) -> None:
        if self._path.exists():
            self._path.unlink()

    async def _launch_browser_cdp(
        self,
        executable_path: str,
        browser_name: str,
        cdp_port: int,
        user_data_dir: str,
    ) -> subprocess.Popen[bytes]:
        """Launch a browser subprocess with CDP debugging and verify connectivity.

        After launching, checks that (1) the process didn't exit immediately
        (e.g. single-instance errors) and (2) the CDP port actually becomes
        available. If either check fails, the process is killed and an error
        is raised so the caller can try the next browser.

        Args:
            executable_path: Path to the browser executable.
            browser_name: Human-readable browser name for logging.
            cdp_port: TCP port for CDP remote debugging.
            user_data_dir: Temporary user data directory.

        Returns:
            The running subprocess with CDP confirmed ready.

        Raises:
            RuntimeError: If the browser exits immediately or CDP is not
                available within the timeout.
        """
        import signal

        proc = subprocess.Popen(
            [
                executable_path,
                f"--remote-debugging-port={cdp_port}",
                f"--user-data-dir={user_data_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "--lang=ja-JP",
                AMAZON_LOGIN_URL,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        logger.info(
            "Launched %s (PID %d) with CDP on port %d",
            browser_name,
            proc.pid,
            cdp_port,
        )

        # Wait briefly to check if the process exits immediately
        # (e.g. Arc: "Only one instance can be opened at a time")
        await asyncio.sleep(1)
        if proc.poll() is not None:
            stderr_output = ""
            if proc.stderr:
                stderr_output = proc.stderr.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"{browser_name}を起動できませんでした"
                f" (exit code {proc.returncode})" + (f": {stderr_output}" if stderr_output else "")
            )

        # Verify CDP port is actually accepting connections.
        # Some browsers (e.g. Arc) ignore --remote-debugging-port.
        try:
            await _wait_for_cdp_ready(cdp_port)
        except RuntimeError:
            # Kill the unresponsive browser before raising
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            raise RuntimeError(
                f"{browser_name}がCDPポートを開きませんでした。"
                f"--remote-debugging-port が無視された可能性があります。"
            )

        return proc

    async def browser_login(self) -> CookieStatus:
        """Launch the user's Chromium-based browser for Amazon login via CDP.

        Auto-detects installed Chromium-based browsers (Arc, Chrome, Brave,
        Edge, Chromium) and tries each in priority order. If a browser
        fails to launch (e.g. single-instance browsers like Arc that are
        already open), automatically falls back to the next available
        browser. Connects via CDP using Playwright.

        The user logs in normally (including 2FA/CAPTCHA). Once login is
        confirmed by checking the account nav text, cookies are captured
        and saved.

        Returns:
            Cookie status after saving the captured cookies.

        Raises:
            TimeoutError: If login is not completed within the timeout period.
            RuntimeError: If no compatible browser could be launched, login
                verification fails, or no cookies captured.
        """

        from app.automation.browser_semaphore import get_browser_semaphore

        async with get_browser_semaphore():
            return await self._browser_login_inner()

    async def _browser_login_inner(self) -> CookieStatus:
        """Inner implementation of browser_login (runs under semaphore)."""
        import shutil
        import signal
        import tempfile

        from playwright.async_api import async_playwright

        available_browsers = _detect_chromium_browsers()

        # Session cookie names that Amazon sets only after successful login
        _login_cookie_names = {"session-id", "session-token", "ubid-acbjp", "x-acbjp"}

        cdp_port = _find_free_port()
        user_data_dir = tempfile.mkdtemp(prefix="shopping_ai_browser_")
        proc: subprocess.Popen[bytes] | None = None

        # Try each browser until one successfully launches
        launch_errors: list[str] = []
        launched_browser_name = ""
        for browser_name, executable_path in available_browsers:
            try:
                proc = await self._launch_browser_cdp(
                    executable_path, browser_name, cdp_port, user_data_dir
                )
                launched_browser_name = browser_name
                break
            except RuntimeError as e:
                logger.warning("Failed to launch %s: %s", browser_name, e)
                launch_errors.append(f"{browser_name}: {e}")
                # Get a new port for the next attempt
                cdp_port = _find_free_port()

        if proc is None:
            raise RuntimeError(
                "起動可能なブラウザが見つかりませんでした。"
                "他のブラウザをすべて閉じてからもう一度お試しいただくか、"
                "Google Chromeをインストールしてください。\n" + "\n".join(launch_errors)
            )

        logger.info(
            "Starting browser login flow with %s via CDP (timeout: %ds)",
            launched_browser_name,
            LOGIN_TIMEOUT_SEC,
        )

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
                try:
                    # Use the first context (the one opened with AMAZON_LOGIN_URL)
                    contexts = browser.contexts
                    if not contexts:
                        raise RuntimeError(
                            "ブラウザコンテキストが取得できませんでした。"
                            "ブラウザが正しく起動しているか確認してください。"
                        )
                    context = contexts[0]
                    pages = context.pages
                    if not pages:
                        raise RuntimeError(
                            "ブラウザページが取得できませんでした。"
                            "ブラウザが正しく起動しているか確認してください。"
                        )
                    page = pages[0]

                    # Verify the Amazon login page actually loaded
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    initial_url = page.url
                    logger.info("Browser initial URL: %s", initial_url)

                    if "amazon.co.jp" not in initial_url:
                        raise RuntimeError(
                            f"Amazonのログインページを開けませんでした (URL: {initial_url})。"
                            "ネットワーク接続を確認してください。"
                        )

                    logger.info("Amazon login page loaded, waiting for user to log in...")

                    # Poll for login completion
                    deadline = time.monotonic() + LOGIN_TIMEOUT_SEC
                    logged_in = False

                    while time.monotonic() < deadline:
                        # Check if browser process is still alive
                        if proc.poll() is not None:
                            raise RuntimeError(
                                "ブラウザが予期せず終了しました。もう一度お試しください。"
                            )

                        await asyncio.sleep(2)
                        current_url = page.url
                        logger.debug("Current URL: %s", current_url)

                        # Still on auth pages — keep waiting
                        if "/ap/" in current_url:
                            continue

                        if "amazon.co.jp" not in current_url:
                            continue

                        try:
                            nav_el = await page.wait_for_selector(
                                "#nav-link-accountList",
                                timeout=5000,
                            )
                            if not nav_el:
                                continue

                            nav_text = await nav_el.text_content()
                            logger.debug("Nav text: %s", nav_text)

                            # "ログイン" means NOT logged in
                            if nav_text and "ログイン" in nav_text:
                                logger.debug("Nav shows login prompt — not logged in yet")
                                continue

                            # Nav shows account name — logged in
                            if nav_text and nav_text.strip():
                                logger.info(
                                    "Login confirmed: nav text = %s",
                                    nav_text.strip(),
                                )
                                logged_in = True
                                break
                        except Exception as e:
                            logger.debug("Could not read nav element: %s", e)
                            continue

                    if not logged_in:
                        raise TimeoutError(
                            f"ログインが{LOGIN_TIMEOUT_SEC}秒以内に完了しませんでした。"
                            "ブラウザでAmazonにログインしてください。"
                        )

                    # Give a moment for cookies to settle after login
                    await asyncio.sleep(2)

                    # Capture all cookies from the browser context
                    raw_cookies = await context.cookies()
                    logger.info("Captured %d cookies from browser", len(raw_cookies))

                    # Convert to our CookieEntry model — only Amazon cookies
                    def _is_amazon_domain(domain: str) -> bool:
                        return domain == "amazon.co.jp" or domain.endswith(".amazon.co.jp")

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
                        if _is_amazon_domain(c.get("domain", ""))
                    ]

                    if not entries:
                        raise RuntimeError(
                            "Amazon関連のCookieが取得できませんでした。"
                            "ログインが正しく完了したか確認してください。"
                        )

                    # Verify session cookies exist (not just tracking cookies)
                    entry_names = {e.name for e in entries}
                    has_session = bool(entry_names & _login_cookie_names)
                    if not has_session:
                        raise RuntimeError(
                            "ログインセッションのCookieが見つかりませんでした。"
                            "Amazonに正しくログインできたか確認してください。"
                        )

                    logger.info(
                        "Captured %d Amazon cookies (%d total), session cookies: %s",
                        len(entries),
                        len(raw_cookies),
                        entry_names & _login_cookie_names,
                    )

                finally:
                    await browser.close()

        finally:
            # Terminate the browser subprocess
            if proc is not None and proc.poll() is None:
                logger.info("Terminating browser process (PID %d)", proc.pid)
                proc.send_signal(signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            # Clean up temp user data directory
            shutil.rmtree(user_data_dir, ignore_errors=True)

        return await self.save_cookies(entries)
