from fastapi import APIRouter, HTTPException

from app.models.settings import CookieStatus, CookieUploadRequest
from app.services.cookie_manager import CookieManagerService

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


@router.delete("/cookies")
async def delete_cookies() -> dict:
    """Delete all stored cookies."""
    await _cookie_manager.delete_cookies()
    return {"message": "Cookieを削除しました"}
