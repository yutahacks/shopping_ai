"""Bearer token authentication middleware.

When API_SECRET_KEY is configured, all API requests must include
a valid Authorization: Bearer <token> header. Authentication is
enforced by default — set ALLOW_UNAUTHENTICATED=true to skip
(development only).
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

logger = logging.getLogger(__name__)

# Paths that never require authentication
PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Validates Bearer token on API requests when API_SECRET_KEY is set."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip auth for public paths
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Skip auth for CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip auth only when explicitly allowed AND no key is configured
        if not settings.api_secret_key and settings.allow_unauthenticated:
            return await call_next(request)

        # Reject if no secret key is configured and unauthenticated access is not allowed
        if not settings.api_secret_key:
            logger.error(
                "API_SECRET_KEY is not configured and ALLOW_UNAUTHENTICATED is not set. "
                "Set API_SECRET_KEY or ALLOW_UNAUTHENTICATED=true."
            )
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "API_SECRET_KEYが設定されていません。"
                    "環境変数を設定するか、開発時はALLOW_UNAUTHENTICATED=trueを設定してください。"
                },
            )

        # Validate Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("Missing or invalid Authorization header from %s", request.client)
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "認証が必要です。"
                    "Authorization: Bearer <token> ヘッダーを含めてください。"
                },
            )

        token = auth_header.removeprefix("Bearer ").strip()
        if token != settings.api_secret_key:
            logger.warning("Invalid API token from %s", request.client)
            return JSONResponse(
                status_code=401,
                content={"detail": "無効なAPIトークンです。"},
            )

        return await call_next(request)
