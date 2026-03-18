import json
from datetime import datetime, timezone

from app.models.shopping import ShoppingPlan, ShoppingSession
from app.storage.database import get_db


class ShoppingHistoryRepository:
    async def save_plan(self, plan: ShoppingPlan) -> None:
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
                    datetime.now(timezone.utc).isoformat(),
                    plan.model_dump_json(),
                ),
            )
            await db.commit()

    async def get_plan(self, session_id: str) -> ShoppingPlan | None:
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
        db = await get_db()
        async with db:
            await db.execute(
                "UPDATE shopping_sessions SET executed = 1 WHERE session_id = ?",
                (session_id,),
            )
            await db.commit()
