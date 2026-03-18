"""Data models for user-defined shopping rules.

Includes avoidance rules, brand preferences, price strategies, and
the top-level container that groups them together.
"""

from typing import Literal

from pydantic import BaseModel, Field


class AvoidRule(BaseModel):
    """Rule to avoid specific items or ingredients.

    Attributes:
        item_pattern: Keyword pattern for items to avoid.
        reason: Optional explanation for the avoidance.
        override_keyword: Keyword that disables this rule when present
            in the user request.
    """

    item_pattern: str = Field(..., description="避けたい食材・商品のキーワード")
    reason: str | None = Field(None, description="避ける理由")
    override_keyword: str | None = Field(
        None, description="このキーワードがリクエストにある場合はルールを無効化"
    )


class BrandRule(BaseModel):
    """Rule to prefer a specific brand for a product category.

    Attributes:
        product_pattern: Keyword pattern for the product category.
        brand: Preferred brand name.
        reason: Optional explanation for the preference.
    """

    product_pattern: str = Field(..., description="商品カテゴリのキーワード")
    brand: str = Field(..., description="優先ブランド名")
    reason: str | None = Field(None, description="このブランドを選ぶ理由")


class PricePreference(BaseModel):
    """Price strategy settings for product selection.

    Attributes:
        strategy: Pricing strategy (cheapest, value, or premium).
        max_price_per_item: Maximum allowed price per item in JPY.
    """

    strategy: Literal["cheapest", "value", "premium"] = Field(
        "cheapest", description="価格戦略: cheapest=最安値, value=コスパ重視, premium=品質重視"
    )
    max_price_per_item: int | None = Field(None, description="1商品の最大価格（円）")


class ShoppingRules(BaseModel):
    """Top-level container for all shopping rules.

    Attributes:
        avoid: List of item avoidance rules.
        brands: List of brand preference rules.
        price: Price strategy preferences.
        notes: Free-form instructions for the AI planner.
    """

    avoid: list[AvoidRule] = Field(default_factory=list)
    brands: list[BrandRule] = Field(default_factory=list)
    price: PricePreference = Field(default_factory=PricePreference)
    notes: str | None = Field(None, description="AIへの自由記述指示")
