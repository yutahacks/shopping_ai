"""Repository for persisting and querying shopping session history.

Stores shopping plans and execution records in SQLite via the
database module.
"""

import logging
from datetime import UTC, datetime

from app.models.cart import CartExecutionResult
from app.models.shopping import ShoppingItem, ShoppingPlan, ShoppingSession
from app.storage.database import get_db

logger = logging.getLogger(__name__)


class ShoppingHistoryRepository:
    """Data access layer for shopping sessions and plans."""

    async def save_plan(self, plan: ShoppingPlan) -> None:
        """Saves or replaces a shopping plan in the database.

        Args:
            plan: The shopping plan to persist.
        """
        async with get_db() as db:
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
        async with get_db() as db:
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
        async with get_db() as db:
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
        async with get_db() as db:
            await db.execute(
                "UPDATE shopping_sessions SET executed = 1 WHERE session_id = ?",
                (session_id,),
            )
            await db.commit()

    async def update_plan_items(self, session_id: str, items: list[ShoppingItem]) -> ShoppingPlan | None:
        """Updates the items in an existing shopping plan.

        Args:
            session_id: The session whose items should be updated.
            items: The new list of items.

        Returns:
            The updated plan, or None if the session was not found.
        """
        plan = await self.get_plan(session_id)
        if plan is None:
            return None

        plan.items = items
        async with get_db() as db:
            await db.execute(
                "UPDATE shopping_sessions SET plan_json = ? WHERE session_id = ?",
                (plan.model_dump_json(), session_id),
            )
            await db.commit()
        logger.info("Updated plan items for session %s (%d items)", session_id, len(items))
        return plan

    async def save_cart_execution(self, result: CartExecutionResult) -> None:
        """Persists a cart execution result to the database.

        Args:
            result: The cart execution result to save.
        """
        async with get_db() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO cart_executions
                    (execution_id, session_id, executed_at, result_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    result.execution_id,
                    result.session_id,
                    datetime.now(UTC).isoformat(),
                    result.model_dump_json(),
                ),
            )
            await db.commit()

    async def get_cart_execution(self, execution_id: str) -> CartExecutionResult | None:
        """Retrieves a cart execution result by execution ID.

        Args:
            execution_id: Unique identifier of the execution.

        Returns:
            The execution result, or None if not found.
        """
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT result_json FROM cart_executions WHERE execution_id = ?",
                (execution_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return CartExecutionResult.model_validate_json(row["result_json"])

    async def get_executions_for_session(self, session_id: str) -> list[CartExecutionResult]:
        """Retrieves all cart executions for a given session.

        Args:
            session_id: The shopping session ID.

        Returns:
            List of execution results ordered by execution time descending.
        """
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT result_json FROM cart_executions
                WHERE session_id = ?
                ORDER BY executed_at DESC
                """,
                (session_id,),
            )
            rows = await cursor.fetchall()
            return [
                CartExecutionResult.model_validate_json(row["result_json"])
                for row in rows
            ]
