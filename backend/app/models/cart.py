from typing import Literal
from pydantic import BaseModel, Field


class CartExecutionRequest(BaseModel):
    session_id: str = Field(..., description="ShoppingPlanのセッションID")
    dry_run: bool = Field(False, description="Trueの場合、実際にカートに追加しない")


class CartItemResult(BaseModel):
    item_name: str
    status: Literal["added", "not_found", "skipped", "error"]
    product_found: str | None = Field(None, description="実際に見つかった商品名")
    price: int | None = Field(None, description="実際の価格（円）")
    asin: str | None = None
    error_message: str | None = None


class CartExecutionResult(BaseModel):
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
    execution_id: str
    event_type: Literal["started", "item_processed", "completed", "error"]
    current_item: str | None = None
    item_result: CartItemResult | None = None
    progress: int = 0
    total: int = 0
    message: str | None = None
