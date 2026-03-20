"""SQLite database connection and schema initialization.

Provides helpers to obtain async database connections and to create
the required tables on application startup.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aiosqlite

from app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Opens and yields an async SQLite connection.

    Yields:
        An aiosqlite Connection with row factory set to Row.
    """
    db = await aiosqlite.connect(str(settings.database_path))
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db() -> None:
    """Creates database tables if they do not already exist."""
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    async with get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shopping_sessions (
                session_id TEXT PRIMARY KEY,
                user_request TEXT NOT NULL,
                context TEXT,
                created_at TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                executed INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cart_executions (
                execution_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                executed_at TEXT NOT NULL,
                result_json TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES shopping_sessions(session_id)
            )
        """)
        await db.commit()
    logger.info("Database tables initialized at %s", settings.database_path)
