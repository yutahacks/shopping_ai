"""Unit tests for ShoppingHistoryRepository — CRUD operations."""

import pytest

from app.models.cart import CartExecutionResult, CartItemResult
from app.models.shopping import ShoppingItem, ShoppingPlan
from app.storage.database import init_db
from app.storage.history_repo import ShoppingHistoryRepository


@pytest.fixture
async def repo(tmp_path, monkeypatch):
    """Create a repository pointing to a temporary test database."""
    db_path = tmp_path / "test.db"
    from app.config import settings

    monkeypatch.setattr(settings, "database_path", db_path)
    await init_db()
    return ShoppingHistoryRepository()


@pytest.fixture
def sample_plan() -> ShoppingPlan:
    """Create a sample shopping plan."""
    return ShoppingPlan(
        session_id="test-session-1",
        user_request="カレーを4人分",
        items=[
            ShoppingItem(name="牛肉", quantity="300g", estimated_price=800, excluded=False),
            ShoppingItem(name="玉ねぎ", quantity="2個", estimated_price=100, excluded=False),
            ShoppingItem(
                name="じゃがいも",
                quantity="3個",
                excluded=True,
                exclusion_reason="avoidルール",
            ),
        ],
        reasoning="テスト用プラン",
        rules_applied=["じゃがいも除外"],
    )


@pytest.mark.asyncio
async def test_save_and_get_plan(
    repo: ShoppingHistoryRepository,
    sample_plan: ShoppingPlan,
) -> None:
    """Plans can be saved and retrieved."""
    await repo.save_plan(sample_plan)
    loaded = await repo.get_plan("test-session-1")
    assert loaded is not None
    assert loaded.user_request == "カレーを4人分"
    assert len(loaded.items) == 3


@pytest.mark.asyncio
async def test_get_plan_not_found(repo: ShoppingHistoryRepository) -> None:
    """Getting a non-existent plan returns None."""
    assert await repo.get_plan("nonexistent") is None


@pytest.mark.asyncio
async def test_list_sessions(repo: ShoppingHistoryRepository, sample_plan: ShoppingPlan) -> None:
    """Sessions can be listed with proper counts."""
    await repo.save_plan(sample_plan)

    plan2 = ShoppingPlan(
        session_id="test-session-2",
        user_request="味噌汁の材料",
        items=[ShoppingItem(name="豆腐", quantity="1丁", excluded=False)],
        reasoning="テスト",
    )
    await repo.save_plan(plan2)

    sessions = await repo.list_sessions()
    assert len(sessions) == 2
    # Most recent first
    assert sessions[0].session_id == "test-session-2"


@pytest.mark.asyncio
async def test_mark_executed(repo: ShoppingHistoryRepository, sample_plan: ShoppingPlan) -> None:
    """Sessions can be marked as executed."""
    await repo.save_plan(sample_plan)
    await repo.mark_executed("test-session-1")

    sessions = await repo.list_sessions()
    assert sessions[0].executed is True


@pytest.mark.asyncio
async def test_update_plan_items(
    repo: ShoppingHistoryRepository,
    sample_plan: ShoppingPlan,
) -> None:
    """Plan items can be updated."""
    await repo.save_plan(sample_plan)

    new_items = [
        ShoppingItem(name="豚肉", quantity="200g", estimated_price=600, excluded=False),
    ]
    updated = await repo.update_plan_items("test-session-1", new_items)
    assert updated is not None
    assert len(updated.items) == 1
    assert updated.items[0].name == "豚肉"

    # Verify persistence
    reloaded = await repo.get_plan("test-session-1")
    assert reloaded is not None
    assert len(reloaded.items) == 1


@pytest.mark.asyncio
async def test_update_plan_items_not_found(repo: ShoppingHistoryRepository) -> None:
    """Updating items for non-existent session returns None."""
    assert await repo.update_plan_items("nonexistent", []) is None


@pytest.mark.asyncio
async def test_save_and_get_cart_execution(
    repo: ShoppingHistoryRepository, sample_plan: ShoppingPlan
) -> None:
    """Cart executions can be saved and retrieved."""
    await repo.save_plan(sample_plan)

    execution = CartExecutionResult(
        execution_id="exec-1",
        session_id="test-session-1",
        status="completed",
        items=[
            CartItemResult(item_name="牛肉", status="added", product_found="和牛 300g", price=850),
            CartItemResult(item_name="玉ねぎ", status="added", price=98),
        ],
        total_items=2,
        added_count=2,
    )
    await repo.save_cart_execution(execution)

    loaded = await repo.get_cart_execution("exec-1")
    assert loaded is not None
    assert loaded.status == "completed"
    assert loaded.added_count == 2
    assert len(loaded.items) == 2


@pytest.mark.asyncio
async def test_get_executions_for_session(
    repo: ShoppingHistoryRepository, sample_plan: ShoppingPlan
) -> None:
    """Multiple executions for a session can be retrieved."""
    await repo.save_plan(sample_plan)

    for i in range(3):
        execution = CartExecutionResult(
            execution_id=f"exec-{i}",
            session_id="test-session-1",
            status="completed",
            total_items=2,
            added_count=2,
        )
        await repo.save_cart_execution(execution)

    executions = await repo.get_executions_for_session("test-session-1")
    assert len(executions) == 3
