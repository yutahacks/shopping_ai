"""FastAPI application entry point for the Shopping AI backend.

Configures the application with CORS middleware, API routes, and
database initialization on startup.
"""

import logging
import sys
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.middleware.auth import BearerAuthMiddleware
from app.storage.database import init_db

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    """Configure structured logging for the application."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)


def _copy_defaults() -> None:
    """Copy default config files to data directory if they don't exist."""
    import json
    import shutil

    config_dir = settings.config_dir
    data_dir = settings.data_dir

    data_dir.mkdir(parents=True, exist_ok=True)

    # Copy rules.yaml default
    default_rules = config_dir / "rules.yaml.default"
    if default_rules.exists() and not settings.rules_path.exists():
        shutil.copy2(default_rules, settings.rules_path)
        logger.info("Copied default rules.yaml to %s", settings.rules_path)

    # Copy profile.json default
    default_profile = config_dir / "profile.json.default"
    if default_profile.exists() and not settings.profile_path.exists():
        shutil.copy2(default_profile, settings.profile_path)
        logger.info("Copied default profile.json to %s", settings.profile_path)
    elif not settings.profile_path.exists():
        # Create empty default profile
        settings.profile_path.parent.mkdir(parents=True, exist_ok=True)
        settings.profile_path.write_text(
            json.dumps({"members": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Created empty profile.json at %s", settings.profile_path)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and shutdown lifecycle.

    Args:
        app: The FastAPI application instance.

    Yields:
        None after database initialization is complete.
    """
    _setup_logging()
    logger.info("Starting Shopping AI Backend v%s", app.version)
    logger.info("OpenAI model: %s", settings.openai_model)
    logger.info("Data directory: %s", settings.data_dir)
    auth_status = "enabled (API_SECRET_KEY set)" if settings.api_secret_key else "disabled"
    logger.info("Auth: %s", auth_status)
    _copy_defaults()
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down Shopping AI Backend")


app = FastAPI(
    title="Shopping AI Backend",
    description="Amazon Fresh Japan Shopping Assistant API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(BearerAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.middleware("http")
async def add_security_headers(
    request: Request,  # noqa: ARG001
    call_next: Callable[..., Awaitable[Response]],
) -> Response:
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    """Returns a simple health check response.

    Returns:
        A dict with status "ok".
    """
    return {"status": "ok"}
