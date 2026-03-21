"""API endpoints for shopping plan generation, editing, and session management."""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.models.shopping import PlanRequest, ShoppingItem, ShoppingPlan, ShoppingSession
from app.rate_limit import limiter
from app.services.planner import ShoppingPlannerService
from app.services.profile_manager import ProfileManagerService
from app.services.rules_manager import RulesManagerService
from app.storage.history_repo import ShoppingHistoryRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/shopping", tags=["shopping"])

_planner = ShoppingPlannerService()
_rules_manager = RulesManagerService()
_profile_manager = ProfileManagerService()
_history_repo = ShoppingHistoryRepository()


class UpdateItemsRequest(BaseModel):
    """Request to replace all items in a plan."""

    items: list[ShoppingItem] = Field(..., description="更新後のアイテムリスト")


class AddItemRequest(BaseModel):
    """Request to add a single item to a plan."""

    item: ShoppingItem = Field(..., description="追加するアイテム")


class ReuseSessionRequest(BaseModel):
    """Request to reuse a past session as a new plan."""

    session_id: str = Field(..., description="再利用するセッションID")


@router.post("/plan", response_model=ShoppingPlan)
@limiter.limit("10/minute")
async def create_shopping_plan(request: Request, plan_request: PlanRequest) -> ShoppingPlan:
    """Generate a shopping plan from a natural language request.

    The plan considers the household profile, shopping rules, and
    the user's natural language request to produce a structured
    shopping list.
    """
    rules = await _rules_manager.get_rules()
    profile = await _profile_manager.get_profile()
    profile_section = profile.to_prompt_section()

    # Build history section from recent sessions
    history_section = await _build_history_section()

    plan = await _planner.create_plan(
        plan_request, rules, profile_section=profile_section, history_section=history_section
    )
    await _history_repo.save_plan(plan)
    return plan


@router.get("/sessions", response_model=list[ShoppingSession])
async def list_sessions(limit: int = 50, offset: int = 0) -> list[ShoppingSession]:
    """List past shopping sessions."""
    return await _history_repo.list_sessions(limit=limit, offset=offset)


@router.get("/sessions/{session_id}", response_model=ShoppingPlan)
async def get_session(session_id: str) -> ShoppingPlan:
    """Get the shopping plan for a specific session."""
    plan = await _history_repo.get_plan(session_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return plan


@router.put("/sessions/{session_id}/items", response_model=ShoppingPlan)
async def update_items(session_id: str, request: UpdateItemsRequest) -> ShoppingPlan:
    """Replace all items in a plan."""
    plan = await _history_repo.update_plan_items(session_id, request.items)
    if plan is None:
        raise HTTPException(status_code=404, detail="Session not found")
    logger.info("Updated items for session %s", session_id)
    return plan


@router.post("/sessions/{session_id}/items", response_model=ShoppingPlan)
async def add_item(session_id: str, request: AddItemRequest) -> ShoppingPlan:
    """Add a single item to a plan."""
    plan = await _history_repo.get_plan(session_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Session not found")

    plan.items.append(request.item)
    updated = await _history_repo.update_plan_items(session_id, plan.items)
    if updated is None:
        raise HTTPException(status_code=500, detail="Failed to update plan")
    return updated


@router.delete("/sessions/{session_id}/items/{item_index}", response_model=ShoppingPlan)
async def remove_item(session_id: str, item_index: int) -> ShoppingPlan:
    """Remove an item from a plan by index."""
    plan = await _history_repo.get_plan(session_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if item_index < 0 or item_index >= len(plan.items):
        raise HTTPException(status_code=400, detail="無効なアイテムインデックスです")

    plan.items.pop(item_index)
    updated = await _history_repo.update_plan_items(session_id, plan.items)
    if updated is None:
        raise HTTPException(status_code=500, detail="Failed to update plan")
    return updated


@router.patch("/sessions/{session_id}/items/{item_index}", response_model=ShoppingPlan)
async def update_item(session_id: str, item_index: int, item: ShoppingItem) -> ShoppingPlan:
    """Update a specific item in a plan."""
    plan = await _history_repo.get_plan(session_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if item_index < 0 or item_index >= len(plan.items):
        raise HTTPException(status_code=400, detail="無効なアイテムインデックスです")

    plan.items[item_index] = item
    updated = await _history_repo.update_plan_items(session_id, plan.items)
    if updated is None:
        raise HTTPException(status_code=500, detail="Failed to update plan")
    return updated


@router.post("/reuse", response_model=ShoppingPlan)
async def reuse_session(request: ReuseSessionRequest) -> ShoppingPlan:
    """Create a new plan by copying items from a past session."""
    original = await _history_repo.get_plan(request.session_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Session not found")

    new_plan = ShoppingPlan(
        user_request=original.user_request,
        context=original.context,
        items=original.items,
        reasoning=f"過去のプランを再利用（元セッション: {request.session_id}）",
        rules_applied=original.rules_applied,
    )
    await _history_repo.save_plan(new_plan)
    logger.info("Reused session %s as new session %s", request.session_id, new_plan.session_id)
    return new_plan


async def _build_history_section(limit: int = 5) -> str:
    """Build a history section from recent sessions for the AI prompt."""
    sessions = await _history_repo.list_sessions(limit=limit)
    if not sessions:
        return ""

    lines: list[str] = []
    for session in sessions:
        plan = await _history_repo.get_plan(session.session_id)
        if plan is None:
            continue
        active_items = [i for i in plan.items if not i.excluded]
        item_names = ", ".join(i.name for i in active_items[:10])
        lines.append(f"- {session.user_request}: {item_names}")

    return "\n".join(lines) if lines else ""
