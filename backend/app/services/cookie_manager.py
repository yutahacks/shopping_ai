"""Service for managing Amazon session cookies.

Provides storage, validation, and lifecycle management for browser
cookies used to authenticate with Amazon Fresh.
"""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings
from app.models.settings import CookieEntry, CookieStatus


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
        return await self.get_status()

    async def delete_cookies(self) -> None:
        """Deletes the stored cookies file from disk."""
        async with self._lock:
            await asyncio.to_thread(self._delete_cookies)

    async def load_cookies(self) -> list[CookieEntry]:
        """Loads and returns all stored cookies.

        Returns:
            List of cookie entries, or an empty list if none exist.
        """
        async with self._lock:
            return await asyncio.to_thread(self._read_cookies)

    def _check_status(self) -> CookieStatus:
        if not self._path.exists():
            return CookieStatus(has_cookies=False, message="Cookieが設定されていません")

        cookies = self._read_cookies()
        if not cookies:
            return CookieStatus(has_cookies=False, message="Cookie файルが空です")

        now = datetime.now(UTC).timestamp()
        valid_cookies = [c for c in cookies if c.expires is None or c.expires > now]

        stat = self._path.stat()
        last_updated = datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()

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

    def _delete_cookies(self) -> None:
        if self._path.exists():
            self._path.unlink()
