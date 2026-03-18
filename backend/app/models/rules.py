from typing import Literal
from pydantic import BaseModel, Field


class AvoidRule(BaseModel):
    item_pattern: str = Field(..., description="避けたい食材・商品のキーワード")
    reason: str | None = Field(None, description="避ける理由")
    override_keyword: str | None = Field(
        None,
        description="このキーワードがリクエストにある場合はルールを無効化"
    )


class BrandRule(BaseModel):
    product_pattern: str = Field(..., description="商品カテゴリのキーワード")
    brand: str = Field(..., description="優先ブランド名")
    reason: str | None = Field(None, description="このブランドを選ぶ理由")


class PricePreference(BaseModel):
    strategy: Literal["cheapest", "value", "premium"] = Field(
        "cheapest",
        description="価格戦略: cheapest=最安値, value=コスパ重視, premium=品質重視"
    )
    max_price_per_item: int | None = Field(None, description="1商品の最大価格（円）")


class ShoppingRules(BaseModel):
    avoid: list[AvoidRule] = Field(default_factory=list)
    brands: list[BrandRule] = Field(default_factory=list)
    price: PricePreference = Field(default_factory=PricePreference)
    notes: str | None = Field(None, description="AIへの自由記述指示")
