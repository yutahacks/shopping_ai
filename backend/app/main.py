"""FastAPI application entry point for the Shopping AI backend.

Configures the application with CORS middleware, API routes, and
database initialization on startup.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.storage.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and shutdown lifecycle.

    Args:
        app: The FastAPI application instance.

    Yields:
        None after database initialization is complete.
    """
    await init_db()
    yield


app = FastAPI(
    title="Shopping AI Backend",
    description="Amazon Fresh Japan Shopping Assistant API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health() -> dict:
    """Returns a simple health check response.

    Returns:
        A dict with status "ok".
    """
    return {"status": "ok"}
