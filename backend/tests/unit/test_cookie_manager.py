"""Unit tests for CookieManagerService — browser login and cookie lifecycle."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.settings import CookieEntry
from app.services.cookie_manager import CookieManagerService


@pytest.fixture
def cookie_manager(tmp_path):
    """Cookie manager with a temp file path."""
    return CookieManagerService(cookies_path=tmp_path / "cookies.json")


@pytest.mark.asyncio
async def test_save_and_load_cookies(cookie_manager):
    """Cookies can be saved and loaded back."""
    cookies = [
        CookieEntry(name="session-id", value="abc", domain=".amazon.co.jp"),
        CookieEntry(name="csm-hit", value="xyz", domain=".amazon.co.jp"),
    ]
    status = await cookie_manager.save_cookies(cookies)
    assert status.has_cookies is True
    assert status.cookie_count == 2

    loaded = await cookie_manager.load_cookies()
    assert len(loaded) == 2
    assert loaded[0].name == "session-id"


@pytest.mark.asyncio
async def test_delete_cookies(cookie_manager):
    """Deleting cookies removes the file."""
    cookies = [CookieEntry(name="test", value="val", domain=".amazon.co.jp")]
    await cookie_manager.save_cookies(cookies)
    await cookie_manager.delete_cookies()

    status = await cookie_manager.get_status()
    assert status.has_cookies is False


@pytest.mark.asyncio
async def test_get_status_no_file(cookie_manager):
    """Status reports no cookies when file does not exist."""
    status = await cookie_manager.get_status()
    assert status.has_cookies is False
    assert status.is_valid is False


@pytest.mark.asyncio
async def test_browser_login_success(cookie_manager):
    """Browser login captures Amazon cookies and saves them."""
    # Mock Playwright objects
    mock_page = AsyncMock()
    mock_page.text_content = AsyncMock(return_value="アカウント＆リスト")

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.cookies = AsyncMock(
        return_value=[
            {
                "name": "session-id",
                "value": "abc123",
                "domain": ".amazon.co.jp",
                "path": "/",
                "secure": True,
                "httpOnly": False,
                "sameSite": "None",
                "expires": 9999999999.0,
            },
            {
                "name": "csm-hit",
                "value": "xyz789",
                "domain": ".amazon.co.jp",
                "path": "/",
                "secure": False,
                "httpOnly": False,
                "sameSite": "Lax",
                "expires": 9999999999.0,
            },
            {
                "name": "unrelated",
                "value": "skip",
                "domain": ".google.com",
                "path": "/",
                "secure": False,
                "httpOnly": False,
            },
        ]
    )

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)

    mock_pw = MagicMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    # Create async context manager mock for async_playwright
    mock_pw_ctx = AsyncMock()
    mock_pw_ctx.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_pw_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "playwright.async_api.async_playwright",
        return_value=mock_pw_ctx,
    ):
        status = await cookie_manager.browser_login()

    assert status.has_cookies is True
    assert status.cookie_count == 2  # Only Amazon cookies, not google.com
    assert status.is_valid is True

    # Verify cookies were saved
    loaded = await cookie_manager.load_cookies()
    names = {c.name for c in loaded}
    assert "session-id" in names
    assert "csm-hit" in names
    assert "unrelated" not in names


@pytest.mark.asyncio
async def test_browser_login_no_amazon_cookies(cookie_manager):
    """Browser login raises error if no Amazon cookies found."""
    mock_page = AsyncMock()
    mock_page.text_content = AsyncMock(return_value="アカウント＆リスト")

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.cookies = AsyncMock(
        return_value=[
            {
                "name": "other",
                "value": "val",
                "domain": ".google.com",
                "path": "/",
                "secure": False,
                "httpOnly": False,
            }
        ]
    )

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)

    mock_pw = MagicMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw_ctx = AsyncMock()
    mock_pw_ctx.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_pw_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(
            "playwright.async_api.async_playwright",
            return_value=mock_pw_ctx,
        ),
        pytest.raises(RuntimeError, match="Amazon関連のCookieが取得できませんでした"),
    ):
        await cookie_manager.browser_login()
