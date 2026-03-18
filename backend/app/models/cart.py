"""Data models for cart execution requests, results, and status events."""

from typing import Literal

from pydantic import BaseModel, Field


class CartExecutionRequest(BaseModel):
    """Request to execute a shopping plan by adding items to the cart.

    Attributes:
        session_id: The shopping plan session ID to execute.
        dry_run: If True, simulates without actually adding to cart.
    """

    session_id: str = Field(..., description="ShoppingPlanのセッションID")
    dry_run: bool = Field(False, description="Trueの場合、実際にカートに追加しない")


class CartItemResult(BaseModel):
    """Result of attempting to add a single item to the cart.

    Attributes:
        item_name: Name of the requested item.
        status: Outcome of the add-to-cart attempt.
        product_found: Actual product name found on Amazon.
        price: Actual price in JPY.
        asin: Amazon Standard Identification Number.
        error_message: Error details if the attempt failed.
    """

    item_name: str
    status: Literal["added", "not_found", "skipped", "error"]
    product_found: str | None = Field(None, description="実際に見つかった商品名")
    price: int | None = Field(None, description="実際の価格（円）")
    asin: str | None = None
    error_message: str | None = None


class CartExecutionResult(BaseModel):
    """Aggregate result of a cart execution across all items.

    Attributes:
        execution_id: Unique identifier for this execution.
        session_id: Associated shopping plan session ID.
        status: Current execution status.
        items: Per-item results.
        total_items: Total number of items to process.
        added_count: Number of items successfully added.
        failed_count: Number of items that failed.
        skipped_count: Number of items skipped.
        error_message: Top-level error if the execution failed.
    """

    execution_id: str
    session_id: str
    status: Literal["pending", "running", "completed", "failed"]
    items: list[CartItemResult] = Field(default_factory=list)
    total_items: int = 0
    added_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    error_message: str | None = None


class CartStatusEvent(BaseModel):
    """Server-sent event representing cart execution progress.

    Attributes:
        execution_id: Unique identifier for the execution.
        event_type: Type of status event.
        current_item: Name of the item currently being processed.
        item_result: Result for the most recently processed item.
        progress: Number of items processed so far.
        total: Total number of items to process.
        message: Human-readable status message.
    """

    execution_id: str
    event_type: Literal["started", "item_processed", "completed", "error"]
    current_item: str | None = None
    item_result: CartItemResult | None = None
    progress: int = 0
    total: int = 0
    message: str | None = None
