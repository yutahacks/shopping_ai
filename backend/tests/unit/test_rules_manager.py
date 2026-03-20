from pathlib import Path

import pytest

from app.models.rules import AvoidRule, BrandRule, PricePreference, ShoppingRules
from app.services.rules_manager import RulesManagerService


@pytest.fixture
def rules_path(tmp_path: Path) -> Path:
    return tmp_path / "rules.yaml"


@pytest.fixture
def rules_manager(rules_path: Path) -> RulesManagerService:
    return RulesManagerService(rules_path=rules_path)


@pytest.mark.asyncio
async def test_get_rules_returns_defaults_when_no_file(rules_manager: RulesManagerService) -> None:
    rules = await rules_manager.get_rules()
    assert rules.avoid == []
    assert rules.brands == []
    assert rules.price.strategy == "cheapest"


@pytest.mark.asyncio
async def test_save_and_get_rules(rules_manager: RulesManagerService) -> None:
    rules = ShoppingRules(
        avoid=[AvoidRule(item_pattern="じゃがいも", reason="嫌い")],
        brands=[BrandRule(product_pattern="シャンプー", brand="パンテーン")],
        price=PricePreference(strategy="value"),
        notes="有機野菜優先",
    )
    await rules_manager.save_rules(rules)
    loaded = await rules_manager.get_rules()
    assert len(loaded.avoid) == 1
    assert loaded.avoid[0].item_pattern == "じゃがいも"
    assert loaded.brands[0].brand == "パンテーン"
    assert loaded.price.strategy == "value"
    assert loaded.notes == "有機野菜優先"


@pytest.mark.asyncio
async def test_update_avoid(rules_manager: RulesManagerService) -> None:
    new_avoid = [AvoidRule(item_pattern="玉ねぎ"), AvoidRule(item_pattern="にんにく")]
    updated = await rules_manager.update_avoid(new_avoid)
    assert len(updated.avoid) == 2


@pytest.mark.asyncio
async def test_update_brands(rules_manager: RulesManagerService) -> None:
    new_brands = [BrandRule(product_pattern="牛乳", brand="明治")]
    updated = await rules_manager.update_brands(new_brands)
    assert updated.brands[0].brand == "明治"
