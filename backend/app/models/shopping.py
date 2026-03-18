"""Data models for shopping plans, items, and session summaries."""

import uuid

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    """Request payload for generating a shopping plan.

    Attributes:
        request: Natural language shopping request.
        context: Optional context such as number of people or budget.
    """

    request: str = Field(..., description="自然言語でのショッピングリクエスト", min_length=1)
    context: str | None = Field(None, description="追加コンテキスト（人数、予算など）")


class ShoppingItem(BaseModel):
    """A single item in a shopping plan.

    Attributes:
        name: Product name.
        quantity: Quantity with unit (e.g., "2 pcs", "300g").
        estimated_price: Estimated price in JPY.
        excluded: Whether the item was excluded by a rule.
        exclusion_reason: Reason for exclusion.
        substitution: Suggested substitute product.
        notes: Additional notes.
    """

    name: str = Field(..., description="商品名")
    quantity: str = Field(..., description="数量（例: 2個、300g）")
    estimated_price: int | None = Field(None, description="予想価格（円）")
    excluded: bool = Field(False, description="ルールにより除外された商品")
    exclusion_reason: str | None = Field(None, description="除外理由")
    substitution: str | None = Field(None, description="代替候補")
    notes: str | None = Field(None, description="備考")


class ShoppingPlan(BaseModel):
    """AI-generated shopping plan with items and reasoning.

    Attributes:
        session_id: Unique session identifier.
        user_request: Original natural language request.
        context: Optional additional context.
        items: List of shopping items in the plan.
        reasoning: Explanation of the planning decisions.
        rules_applied: Descriptions of rules that were applied.
    """

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_request: str
    context: str | None = None
    items: list[ShoppingItem]
    reasoning: str = Field(..., description="プランニングの理由・説明")
    rules_applied: list[str] = Field(default_factory=list, description="適用されたルールの説明")


class ShoppingSession(BaseModel):
    """Summary of a shopping session for history listing.

    Attributes:
        session_id: Unique session identifier.
        user_request: Original natural language request.
        context: Optional additional context.
        created_at: ISO timestamp of session creation.
        item_count: Number of items in the plan.
        executed: Whether the plan has been executed.
    """

    session_id: str
    user_request: str
    context: str | None = None
    created_at: str
    item_count: int
    executed: bool = False
