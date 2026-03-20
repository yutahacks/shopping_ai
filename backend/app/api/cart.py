"""API endpoints for cart execution and status streaming."""

from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.automation.browser import BrowserFactory
from app.models.cart import CartExecutionRequest, CartExecutionResult
from app.services.cart_executor import CartExecutorService
from app.services.cookie_manager import CookieManagerService
from app.storage.history_repo import ShoppingHistoryRepository

router = APIRouter(prefix="/api/cart", tags=["cart"])

_cookie_manager = CookieManagerService()
_browser_factory = BrowserFactory()
_history_repo = ShoppingHistoryRepository()
_executor = CartExecutorService(_cookie_manager, _browser_factory, _history_repo)


@router.post("/execute", response_model=CartExecutionResult)
async def execute_cart(request: CartExecutionRequest) -> CartExecutionResult:
    """Start cart execution for a shopping plan."""
    plan = await _history_repo.get_plan(request.session_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not request.dry_run:
        cookie_status = await _cookie_manager.get_status()
        if not cookie_status.is_valid:
            raise HTTPException(
                status_code=400,
                detail=(
                    "有効なAmazon Cookieがありません。"
                    "設定ページからCookieをアップロードしてください。"
                ),
            )

    result = await _executor.start_execution(plan, dry_run=request.dry_run)
    await _history_repo.mark_executed(request.session_id)
    return result


@router.get("/status/{execution_id}")
async def stream_cart_status(execution_id: str) -> StreamingResponse:
    """Stream cart execution status via Server-Sent Events."""

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in _executor.stream_status(execution_id):
            data = event.model_dump_json()
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/executions/{session_id}", response_model=list[CartExecutionResult])
async def get_executions(session_id: str) -> list[CartExecutionResult]:
    """Get all cart executions for a session."""
    return await _history_repo.get_executions_for_session(session_id)
