"""Repository for persisting and querying shopping session history.

Stores shopping plans and execution records in SQLite via the
database module.
"""

from datetime import UTC, datetime

from app.models.shopping import ShoppingPlan, ShoppingSession
from app.storage.database import get_db


class ShoppingHistoryRepository:
    """Data access layer for shopping sessions and plans."""

    async def save_plan(self, plan: ShoppingPlan) -> None:
        """Saves or replaces a shopping plan in the database.

        Args:
            plan: The shopping plan to persist.
        """
        db = await get_db()
        async with db:
            await db.execute(
                """
                INSERT OR REPLACE INTO shopping_sessions
                    (session_id, user_request, context, created_at, plan_json, executed)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (
                    plan.session_id,
                    plan.user_request,
                    plan.context,
                    datetime.now(UTC).isoformat(),
                    plan.model_dump_json(),
                ),
            )
            await db.commit()

    async def get_plan(self, session_id: str) -> ShoppingPlan | None:
        """Retrieves a shopping plan by session ID.

        Args:
            session_id: Unique identifier of the session.

        Returns:
            The shopping plan, or None if not found.
        """
        db = await get_db()
        async with db:
            cursor = await db.execute(
                "SELECT plan_json FROM shopping_sessions WHERE session_id = ?",
                (session_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return ShoppingPlan.model_validate_json(row["plan_json"])

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> list[ShoppingSession]:
        """Lists shopping sessions ordered by creation date descending.

        Args:
            limit: Maximum number of sessions to return.
            offset: Number of sessions to skip for pagination.

        Returns:
            List of shopping session summaries.
        """
        db = await get_db()
        async with db:
            cursor = await db.execute(
                """
                SELECT session_id, user_request, context, created_at,
                       json_array_length(json_extract(plan_json, '$.items')) as item_count,
                       executed
                FROM shopping_sessions
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            rows = await cursor.fetchall()
            return [
                ShoppingSession(
                    session_id=row["session_id"],
                    user_request=row["user_request"],
                    context=row["context"],
                    created_at=row["created_at"],
                    item_count=row["item_count"] or 0,
                    executed=bool(row["executed"]),
                )
                for row in rows
            ]

    async def mark_executed(self, session_id: str) -> None:
        """Marks a shopping session as executed.

        Args:
            session_id: Unique identifier of the session to mark.
        """
        db = await get_db()
        async with db:
            await db.execute(
                "UPDATE shopping_sessions SET executed = 1 WHERE session_id = ?",
                (session_id,),
            )
            await db.commit()
