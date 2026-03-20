"""Unit tests for CartExecutorService — dry run and DB persistence."""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.shopping import ShoppingItem, ShoppingPlan
from app.services.cart_executor import CartExecutorService, _active_executions
from app.storage.database import init_db
from app.storage.history_repo import ShoppingHistoryRepository


@pytest.fixture
async def history_repo(tmp_path, monkeypatch):
    """Repository with test database."""
    db_path = tmp_path / "test.db"
    from app.config import settings
    monkeypatch.setattr(settings, "database_path", db_path)
    await init_db()
    return ShoppingHistoryRepository()


@pytest.fixture
def sample_plan() -> ShoppingPlan:
    return ShoppingPlan(
        session_id="test-session",
        user_request="テスト",
        items=[
            ShoppingItem(name="牛肉", quantity="300g", excluded=False),
            ShoppingItem(name="玉ねぎ", quantity="2個", excluded=False),
            ShoppingItem(name="じゃがいも", quantity="3個", excluded=True, exclusion_reason="avoid"),
        ],
        reasoning="テスト",
    )


@pytest.mark.asyncio
async def test_dry_run_produces_skipped_results(
    history_repo: ShoppingHistoryRepository,
    sample_plan: ShoppingPlan,
) -> None:
    """Dry run should skip all items without browser interaction."""
    cookie_manager = MagicMock()
    cookie_manager.load_cookies = AsyncMock(return_value=[])

    browser_factory = MagicMock()

    executor = CartExecutorService(cookie_manager, browser_factory, history_repo)

    result = await executor.start_execution(sample_plan, dry_run=True)
    assert result.status == "pending"
    assert result.total_items == 2  # excluded items not counted

    # Wait for background task to complete
    await asyncio.sleep(2.0)

    # Check DB for persisted result
    execution = await history_repo.get_cart_execution(result.execution_id)
    # Also check active executions (may not be cleaned up yet)
    if execution is None:
        execution = _active_executions.get(result.execution_id)

    assert execution is not None
    assert execution.status == "completed"
    assert execution.skipped_count == 2
    assert execution.added_count == 0
