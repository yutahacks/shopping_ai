"""Data models for cookie management and application settings."""

from pydantic import BaseModel, Field


class CookieEntry(BaseModel):
    """Represents a single browser cookie.

    Attributes:
        name: Cookie name.
        value: Cookie value.
        domain: Domain the cookie belongs to.
        path: URL path scope for the cookie.
        secure: Whether the cookie requires HTTPS.
        http_only: Whether the cookie is HTTP-only.
        same_site: SameSite attribute (Strict, Lax, or None).
        expires: Expiration timestamp in seconds since epoch.
    """

    name: str
    value: str
    domain: str
    path: str = "/"
    secure: bool = False
    http_only: bool = False
    same_site: str | None = None
    expires: float | None = None


class CookieStatus(BaseModel):
    """Status summary of stored cookies.

    Attributes:
        has_cookies: Whether any cookies are stored.
        cookie_count: Total number of stored cookies.
        is_valid: Whether at least one cookie is not expired.
        last_updated: ISO timestamp of last cookie file modification.
        message: Human-readable status message.
    """

    has_cookies: bool
    cookie_count: int = 0
    is_valid: bool = False
    last_updated: str | None = None
    message: str = ""


class CookieUploadRequest(BaseModel):
    """Request payload for uploading Amazon session cookies.

    Attributes:
        cookies: List of cookie entries to store.
    """

    cookies: list[CookieEntry] = Field(..., description="Amazonセッションクッキーのリスト")
