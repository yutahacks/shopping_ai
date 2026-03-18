from pydantic import BaseModel, Field
import uuid


class PlanRequest(BaseModel):
    request: str = Field(..., description="自然言語でのショッピングリクエスト", min_length=1)
    context: str | None = Field(None, description="追加コンテキスト（人数、予算など）")


class ShoppingItem(BaseModel):
    name: str = Field(..., description="商品名")
    quantity: str = Field(..., description="数量（例: 2個、300g）")
    estimated_price: int | None = Field(None, description="予想価格（円）")
    excluded: bool = Field(False, description="ルールにより除外された商品")
    exclusion_reason: str | None = Field(None, description="除外理由")
    substitution: str | None = Field(None, description="代替候補")
    notes: str | None = Field(None, description="備考")


class ShoppingPlan(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_request: str
    context: str | None = None
    items: list[ShoppingItem]
    reasoning: str = Field(..., description="プランニングの理由・説明")
    rules_applied: list[str] = Field(default_factory=list, description="適用されたルールの説明")


class ShoppingSession(BaseModel):
    session_id: str
    user_request: str
    context: str | None = None
    created_at: str
    item_count: int
    executed: bool = False
