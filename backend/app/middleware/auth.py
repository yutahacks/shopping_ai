"""Bearer token authentication middleware.

When API_SECRET_KEY is configured, all API requests must include
a valid Authorization: Bearer <token> header. When the key is empty
or not set, authentication is skipped (open access).
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
        # Skip auth if no secret key is configured
        if not settings.api_secret_key:
            return await call_next(request)

        # Skip auth for public paths
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Skip auth for CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        # Validate Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("Missing or invalid Authorization header from %s", request.client)
            return JSONResponse(
                status_code=401,
                content={"detail": "認証が必要です。Authorization: Bearer <token> ヘッダーを含めてください。"},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        if token != settings.api_secret_key:
            logger.warning("Invalid API token from %s", request.client)
            return JSONResponse(
                status_code=401,
                content={"detail": "無効なAPIトークンです。"},
            )

        return await call_next(request)
