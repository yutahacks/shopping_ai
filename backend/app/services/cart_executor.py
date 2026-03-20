"""Service for executing shopping cart operations.

Orchestrates browser automation to search for products on Amazon Fresh
and add them to the cart based on a shopping plan.
"""

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator

from app.automation.amazon_fresh import AmazonFreshAutomator
from app.automation.browser import BrowserFactory
from app.models.cart import (
    CartExecutionResult,
    CartItemResult,
    CartStatusEvent,
)
from app.models.shopping import ShoppingPlan
from app.services.cookie_manager import CookieManagerService
from app.storage.history_repo import ShoppingHistoryRepository

logger = logging.getLogger(__name__)

# In-memory store for active execution tracking (SSE streaming).
# Completed executions are persisted to the database.
_active_executions: dict[str, CartExecutionResult] = {}


class CartExecutorService:
    """Executes shopping plans by automating Amazon Fresh cart additions.

    Attributes:
        _cookie_manager: Service for loading browser cookies.
        _browser_factory: Factory for creating browser pages.
        _history_repo: Repository for persisting execution results.
    """

    def __init__(
        self,
        cookie_manager: CookieManagerService,
        browser_factory: BrowserFactory,
        history_repo: ShoppingHistoryRepository | None = None,
    ) -> None:
        """Initializes the cart executor.

        Args:
            cookie_manager: Service for loading Amazon session cookies.
            browser_factory: Factory for creating Playwright browser pages.
            history_repo: Repository for persisting execution results.
        """
        self._cookie_manager = cookie_manager
        self._browser_factory = browser_factory
        self._history_repo = history_repo or ShoppingHistoryRepository()

    async def start_execution(
        self,
        plan: ShoppingPlan,
        dry_run: bool = False,
    ) -> CartExecutionResult:
        """Starts a cart execution as a background task.

        Args:
            plan: The shopping plan containing items to add.
            dry_run: If True, simulates execution without adding to cart.

        Returns:
            The initial execution result with a pending status.
        """
        execution_id = str(uuid.uuid4())
        active_items = [item for item in plan.items if not item.excluded]

        result = CartExecutionResult(
            execution_id=execution_id,
            session_id=plan.session_id,
            status="pending",
            total_items=len(active_items),
        )
        _active_executions[execution_id] = result
        logger.info(
            "Starting cart execution %s for session %s (%d items, dry_run=%s)",
            execution_id, plan.session_id, len(active_items), dry_run,
        )

        # Start background task
        asyncio.create_task(self._run_execution(execution_id, plan, dry_run))

        return result

    async def get_result(self, execution_id: str) -> CartExecutionResult | None:
        """Retrieves the execution result by ID.

        Checks in-memory active executions first, then falls back to database.

        Args:
            execution_id: Unique identifier of the execution.

        Returns:
            The execution result, or None if not found.
        """
        # Check active in-memory executions first
        result = _active_executions.get(execution_id)
        if result is not None:
            return result
        # Fall back to database
        return await self._history_repo.get_cart_execution(execution_id)

    async def stream_status(self, execution_id: str) -> AsyncGenerator[CartStatusEvent, None]:
        """Polls execution status and yields server-sent events.

        Args:
            execution_id: Unique identifier of the execution to stream.

        Yields:
            CartStatusEvent for each processed item and completion.
        """
        result = _active_executions.get(execution_id)
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
            result = _active_executions.get(execution_id)
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
        result = _active_executions[execution_id]
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
                        result.error_message = (
                            "Amazonにログインしていません。Cookieを更新してください。"
                        )
                        logger.error("Cart execution %s failed: not logged in", execution_id)
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

                    logger.info(
                        "Item '%s': %s (execution %s)",
                        item_result.item_name, item_result.status, execution_id,
                    )

                    # Small delay between items to avoid rate limiting
                    if not dry_run:
                        await asyncio.sleep(1.0)

            result.status = "completed"
            logger.info(
                "Cart execution %s completed: %d added, %d failed, %d skipped",
                execution_id, result.added_count, result.failed_count, result.skipped_count,
            )

        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            logger.exception("Cart execution %s failed with error", execution_id)

        finally:
            # Persist to database
            try:
                await self._history_repo.save_cart_execution(result)
                logger.info("Persisted execution %s to database", execution_id)
            except Exception:
                logger.exception("Failed to persist execution %s to database", execution_id)
            # Clean up from active executions after a delay (allow SSE to finish)
            await asyncio.sleep(5.0)
            _active_executions.pop(execution_id, None)
