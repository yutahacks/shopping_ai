"""Unit tests for CookieManagerService — browser login and cookie lifecycle."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.settings import CookieEntry
from app.services.cookie_manager import CookieManagerService

# Common patches for browser_login tests (CDP-based approach).
# subprocess/shutil/async_playwright are imported inside browser_login,
# so we patch the builtins at their source module.
_BROWSER_LOGIN_PATCHES = {
    "detect": "app.services.cookie_manager._detect_chromium_browsers",
    "port": "app.services.cookie_manager._find_free_port",
    "cdp_ready": "app.services.cookie_manager._wait_for_cdp_ready",
    "popen": "subprocess.Popen",
    "rmtree": "shutil.rmtree",
    "playwright": "playwright.async_api.async_playwright",
}


def _make_browser_login_mocks(
    *,
    nav_text: str = "アカウント＆リスト",
    cookies: list[dict[str, object]] | None = None,
    initial_url: str = "https://www.amazon.co.jp/ap/signin",
    poll_url: str = "https://www.amazon.co.jp/",
) -> dict[str, MagicMock | AsyncMock]:
    """Create mock objects for browser_login CDP flow.

    Returns:
        Dict with keys: page, context, browser, pw, pw_ctx, proc.
    """
    mock_nav_el = AsyncMock()
    mock_nav_el.text_content = AsyncMock(return_value=nav_text)

    mock_page = AsyncMock()
    mock_page.url = poll_url
    mock_page.wait_for_load_state = AsyncMock()
    mock_page.wait_for_selector = AsyncMock(return_value=mock_nav_el)

    if cookies is None:
        cookies = [
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

    mock_context = MagicMock()
    mock_context.pages = [mock_page]
    mock_context.cookies = AsyncMock(return_value=cookies)

    mock_browser = MagicMock()
    mock_browser.contexts = [mock_context]
    mock_browser.close = AsyncMock()

    mock_pw = MagicMock()
    mock_pw.chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

    mock_pw_ctx = AsyncMock()
    mock_pw_ctx.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_pw_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_proc = MagicMock()
    mock_proc.pid = 12345
    mock_proc.poll = MagicMock(return_value=None)
    mock_proc.send_signal = MagicMock()
    mock_proc.wait = MagicMock()

    # Handle initial_url for wait_for_load_state, then poll_url after
    original_url = mock_page.url

    async def _wait_for_load_state_side_effect(*_args: object, **_kwargs: object) -> None:
        mock_page.url = initial_url

    mock_page.wait_for_load_state.side_effect = _wait_for_load_state_side_effect

    # sleep is called: once in _launch_browser_cdp (1s check), then in poll loop.
    # After the launch sleep, switch URL to poll_url for the login check.
    call_count = 0

    async def _sleep_side_effect(_duration: float) -> None:
        nonlocal call_count
        call_count += 1
        # call 1 = _launch_browser_cdp startup check
        # call 2+ = poll loop — set URL to trigger login detection
        if call_count >= 2:
            mock_page.url = original_url

    return {
        "page": mock_page,
        "context": mock_context,
        "browser": mock_browser,
        "pw_ctx": mock_pw_ctx,
        "proc": mock_proc,
        "sleep_side_effect": _sleep_side_effect,
    }


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
    """Browser login captures Amazon cookies and saves them via CDP."""
    mocks = _make_browser_login_mocks()

    with (
        patch(_BROWSER_LOGIN_PATCHES["detect"], return_value=[("Arc", "/usr/bin/arc")]),
        patch(_BROWSER_LOGIN_PATCHES["port"], return_value=9222),
        patch(_BROWSER_LOGIN_PATCHES["cdp_ready"], new_callable=AsyncMock),
        patch(_BROWSER_LOGIN_PATCHES["popen"], return_value=mocks["proc"]),
        patch(_BROWSER_LOGIN_PATCHES["rmtree"]),
        patch(_BROWSER_LOGIN_PATCHES["playwright"], return_value=mocks["pw_ctx"]),
        patch("asyncio.sleep", side_effect=mocks["sleep_side_effect"]),
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
    mocks = _make_browser_login_mocks(
        cookies=[
            {
                "name": "other",
                "value": "val",
                "domain": ".google.com",
                "path": "/",
                "secure": False,
                "httpOnly": False,
            }
        ],
    )

    with (
        patch(_BROWSER_LOGIN_PATCHES["detect"], return_value=[("Chrome", "/usr/bin/chrome")]),
        patch(_BROWSER_LOGIN_PATCHES["port"], return_value=9222),
        patch(_BROWSER_LOGIN_PATCHES["cdp_ready"], new_callable=AsyncMock),
        patch(_BROWSER_LOGIN_PATCHES["popen"], return_value=mocks["proc"]),
        patch(_BROWSER_LOGIN_PATCHES["rmtree"]),
        patch(_BROWSER_LOGIN_PATCHES["playwright"], return_value=mocks["pw_ctx"]),
        patch("asyncio.sleep", side_effect=mocks["sleep_side_effect"]),
        pytest.raises(RuntimeError, match="Amazon関連のCookieが取得できませんでした"),
    ):
        await cookie_manager.browser_login()


@pytest.mark.asyncio
async def test_browser_login_validates_initial_page(cookie_manager):
    """Browser login raises error if Amazon page doesn't load."""
    mocks = _make_browser_login_mocks(initial_url="about:blank")

    with (
        patch(_BROWSER_LOGIN_PATCHES["detect"], return_value=[("Arc", "/usr/bin/arc")]),
        patch(_BROWSER_LOGIN_PATCHES["port"], return_value=9222),
        patch(_BROWSER_LOGIN_PATCHES["cdp_ready"], new_callable=AsyncMock),
        patch(_BROWSER_LOGIN_PATCHES["popen"], return_value=mocks["proc"]),
        patch(_BROWSER_LOGIN_PATCHES["rmtree"]),
        patch(_BROWSER_LOGIN_PATCHES["playwright"], return_value=mocks["pw_ctx"]),
        pytest.raises(RuntimeError, match="Amazonのログインページを開けませんでした"),
    ):
        await cookie_manager.browser_login()


@pytest.mark.asyncio
async def test_browser_login_detects_browser_crash(cookie_manager):
    """Browser login raises error if browser process exits unexpectedly."""
    mocks = _make_browser_login_mocks()
    # poll() returns None during launch check, then 1 (crashed) during poll loop,
    # then 1 again during finally-block cleanup
    mocks["proc"].poll = MagicMock(side_effect=[None, 1, 1])

    with (
        patch(_BROWSER_LOGIN_PATCHES["detect"], return_value=[("Arc", "/usr/bin/arc")]),
        patch(_BROWSER_LOGIN_PATCHES["port"], return_value=9222),
        patch(_BROWSER_LOGIN_PATCHES["cdp_ready"], new_callable=AsyncMock),
        patch(_BROWSER_LOGIN_PATCHES["popen"], return_value=mocks["proc"]),
        patch(_BROWSER_LOGIN_PATCHES["rmtree"]),
        patch(_BROWSER_LOGIN_PATCHES["playwright"], return_value=mocks["pw_ctx"]),
        patch("asyncio.sleep", side_effect=mocks["sleep_side_effect"]),
        pytest.raises(RuntimeError, match="ブラウザが予期せず終了しました"),
    ):
        await cookie_manager.browser_login()


@pytest.mark.asyncio
async def test_browser_login_fallback_on_single_instance(cookie_manager):
    """Falls back to next browser when first one can't launch (e.g. Arc already open)."""
    mocks = _make_browser_login_mocks()

    # First Popen call (Arc): process exits immediately (single-instance error)
    mock_arc_proc = MagicMock()
    mock_arc_proc.pid = 11111
    mock_arc_proc.poll = MagicMock(return_value=1)
    mock_arc_proc.returncode = 1
    mock_arc_proc.stderr = MagicMock()
    mock_arc_proc.stderr.read = MagicMock(
        return_value=b"Arc is already open. Only one instance can be opened at a time."
    )

    # Second Popen call (Chrome): succeeds
    popen_side_effect = [mock_arc_proc, mocks["proc"]]

    with (
        patch(
            _BROWSER_LOGIN_PATCHES["detect"],
            return_value=[("Arc", "/usr/bin/arc"), ("Chrome", "/usr/bin/chrome")],
        ),
        patch(_BROWSER_LOGIN_PATCHES["port"], side_effect=[9222, 9223]),
        patch(_BROWSER_LOGIN_PATCHES["cdp_ready"], new_callable=AsyncMock),
        patch(_BROWSER_LOGIN_PATCHES["popen"], side_effect=popen_side_effect),
        patch(_BROWSER_LOGIN_PATCHES["rmtree"]),
        patch(_BROWSER_LOGIN_PATCHES["playwright"], return_value=mocks["pw_ctx"]),
        patch("asyncio.sleep", side_effect=mocks["sleep_side_effect"]),
    ):
        status = await cookie_manager.browser_login()

    assert status.has_cookies is True
    assert status.cookie_count == 2
