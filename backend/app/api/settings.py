import logging

from fastapi import APIRouter, HTTPException, Request

from app.models.settings import CookieStatus, CookieUploadRequest
from app.rate_limit import limiter
from app.services.cookie_manager import CookieManagerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])

_cookie_manager = CookieManagerService()


@router.get("/cookies/status", response_model=CookieStatus)
async def get_cookie_status() -> CookieStatus:
    """Check the validity of stored Amazon cookies."""
    return await _cookie_manager.get_status()


@router.post("/cookies", response_model=CookieStatus)
@limiter.limit("10/minute")
async def upload_cookies(request: Request, upload_request: CookieUploadRequest) -> CookieStatus:
    """Upload Amazon session cookies."""
    if not upload_request.cookies:
        raise HTTPException(status_code=400, detail="Cookieが空です")
    return await _cookie_manager.save_cookies(upload_request.cookies)


@router.post("/cookies/login", response_model=CookieStatus)
@limiter.limit("2/minute")
async def browser_login(request: Request) -> CookieStatus:
    """Launch a headed browser for the user to log in to Amazon.

    Opens a visible Chromium window. The user logs in manually
    (supports 2FA/CAPTCHA). Cookies are captured and saved automatically.
    """
    try:
        return await _cookie_manager.browser_login()
    except TimeoutError:
        logger.warning("Browser login timed out")
        raise HTTPException(
            status_code=408,
            detail="ログインがタイムアウトしました。もう一度お試しください。",
        )
    except RuntimeError:
        logger.warning("Browser login failed with RuntimeError", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="ブラウザを起動できませんでした。"
            "対応ブラウザがインストールされているか確認してください。",
        )
    except Exception:
        logger.exception("Browser login failed")
        raise HTTPException(
            status_code=500,
            detail="ブラウザログインに失敗しました。もう一度お試しください。",
        )


@router.delete("/cookies")
async def delete_cookies() -> dict[str, str]:
    """Delete all stored cookies."""
    await _cookie_manager.delete_cookies()
    return {"message": "Cookieを削除しました"}
