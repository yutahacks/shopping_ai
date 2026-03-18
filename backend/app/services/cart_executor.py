import asyncio
import uuid
from typing import AsyncGenerator

from app.automation.amazon_fresh import AmazonFreshAutomator
from app.automation.browser import BrowserFactory
from app.models.cart import (
    CartExecutionResult,
    CartItemResult,
    CartStatusEvent,
)
from app.models.shopping import ShoppingPlan
from app.services.cookie_manager import CookieManagerService

# In-memory store for execution results (could be replaced with Redis/DB)
_executions: dict[str, CartExecutionResult] = {}


class CartExecutorService:
    def __init__(
        self,
        cookie_manager: CookieManagerService,
        browser_factory: BrowserFactory,
    ) -> None:
        self._cookie_manager = cookie_manager
        self._browser_factory = browser_factory

    async def start_execution(
        self,
        plan: ShoppingPlan,
        dry_run: bool = False,
    ) -> CartExecutionResult:
        execution_id = str(uuid.uuid4())
        active_items = [item for item in plan.items if not item.excluded]

        result = CartExecutionResult(
            execution_id=execution_id,
            session_id=plan.session_id,
            status="pending",
            total_items=len(active_items),
        )
        _executions[execution_id] = result

        # Start background task
        asyncio.create_task(
            self._run_execution(execution_id, plan, dry_run)
        )

        return result

    async def get_result(self, execution_id: str) -> CartExecutionResult | None:
        return _executions.get(execution_id)

    async def stream_status(
        self, execution_id: str
    ) -> AsyncGenerator[CartStatusEvent, None]:
        """Poll execution status and yield SSE events."""
        result = _executions.get(execution_id)
        if not result:
            return

        sent_count = 0
        yield CartStatusEvent(
            execution_id=execution_id,
            event_type="started",
            total=result.total_items,
            message="カート追加を開始します",
        )

        while True:
            result = _executions.get(execution_id)
            if not result:
                break

            current_count = len(result.items)
            if current_count > sent_count:
                for item in result.items[sent_count:]:
                    yield CartStatusEvent(
                        execution_id=execution_id,
                        event_type="item_processed",
                        item_result=item,
                        progress=current_count,
                        total=result.total_items,
                        message=f"{item.item_name}: {item.status}",
                    )
                sent_count = current_count

            if result.status in ("completed", "failed"):
                yield CartStatusEvent(
                    execution_id=execution_id,
                    event_type="completed",
                    progress=result.total_items,
                    total=result.total_items,
                    message=f"完了: {result.added_count}件追加, {result.failed_count}件失敗",
                )
                break

            await asyncio.sleep(0.5)

    async def _run_execution(
        self,
        execution_id: str,
        plan: ShoppingPlan,
        dry_run: bool,
    ) -> None:
        result = _executions[execution_id]
        result.status = "running"

        try:
            cookies = await self._cookie_manager.load_cookies()
            active_items = [item for item in plan.items if not item.excluded]

            from app.services.rules_manager import RulesManagerService
            rules_manager = RulesManagerService()
            rules = await rules_manager.get_rules()

            async with self._browser_factory.create_page(cookies) as page:
                automator = AmazonFreshAutomator(page, rules)

                # Verify login status
                if not dry_run:
                    is_logged_in = await automator.check_login_status()
                    if not is_logged_in:
                        result.status = "failed"
                        result.error_message = "Amazonにログインしていません。Cookieを更新してください。"
                        return

                for item in active_items:
                    if dry_run:
                        item_result = CartItemResult(
                            item_name=item.name,
                            status="skipped",
                            error_message="ドライランモード",
                        )
                    else:
                        item_result = await automator.search_and_add_to_cart(
                            item.name, item.quantity
                        )

                    result.items.append(item_result)

                    if item_result.status == "added":
                        result.added_count += 1
                    elif item_result.status in ("error", "not_found"):
                        result.failed_count += 1
                    else:
                        result.skipped_count += 1

                    # Small delay between items to avoid rate limiting
                    if not dry_run:
                        await asyncio.sleep(1.0)

            result.status = "completed"

        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
