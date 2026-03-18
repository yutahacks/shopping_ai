from fastapi import APIRouter, HTTPException

from app.models.shopping import PlanRequest, ShoppingPlan, ShoppingSession
from app.services.cookie_manager import CookieManagerService
from app.services.planner import ClaudePlannerService
from app.services.rules_manager import RulesManagerService
from app.storage.history_repo import ShoppingHistoryRepository

router = APIRouter(prefix="/api/shopping", tags=["shopping"])

_planner = ClaudePlannerService()
_rules_manager = RulesManagerService()
_cookie_manager = CookieManagerService()
_history_repo = ShoppingHistoryRepository()


@router.post("/plan", response_model=ShoppingPlan)
async def create_shopping_plan(request: PlanRequest) -> ShoppingPlan:
    """Generate a shopping plan from a natural language request."""
    rules = await _rules_manager.get_rules()
    plan = await _planner.create_plan(request, rules)
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
