from pydantic import BaseModel, Field


class CookieEntry(BaseModel):
    name: str
    value: str
    domain: str
    path: str = "/"
    secure: bool = False
    http_only: bool = False
    same_site: str | None = None
    expires: float | None = None


class CookieStatus(BaseModel):
    has_cookies: bool
    cookie_count: int = 0
    is_valid: bool = False
    last_updated: str | None = None
    message: str = ""


class CookieUploadRequest(BaseModel):
    cookies: list[CookieEntry] = Field(..., description="Amazonセッションクッキーのリスト")
