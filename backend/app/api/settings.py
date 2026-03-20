import logging

from fastapi import APIRouter, HTTPException

from app.models.settings import CookieStatus, CookieUploadRequest
from app.services.cookie_manager import CookieManagerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])

_cookie_manager = CookieManagerService()


@router.get("/cookies/status", response_model=CookieStatus)
async def get_cookie_status() -> CookieStatus:
    """Check the validity of stored Amazon cookies."""
    return await _cookie_manager.get_status()


@router.post("/cookies", response_model=CookieStatus)
async def upload_cookies(request: CookieUploadRequest) -> CookieStatus:
    """Upload Amazon session cookies."""
    if not request.cookies:
        raise HTTPException(status_code=400, detail="Cookieが空です")
    return await _cookie_manager.save_cookies(request.cookies)


@router.post("/cookies/login", response_model=CookieStatus)
async def browser_login() -> CookieStatus:
    """Launch a headed browser for the user to log in to Amazon.

    Opens a visible Chromium window. The user logs in manually
    (supports 2FA/CAPTCHA). Cookies are captured and saved automatically.
    """
    try:
        return await _cookie_manager.browser_login()
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
