from fastapi import APIRouter

from app.models.rules import AvoidRule, BrandRule, PricePreference, ShoppingRules
from app.services.rules_manager import RulesManagerService

router = APIRouter(prefix="/api/rules", tags=["rules"])

_rules_manager = RulesManagerService()


@router.get("", response_model=ShoppingRules)
async def get_rules() -> ShoppingRules:
    """Get current shopping rules."""
    return await _rules_manager.get_rules()


@router.put("", response_model=ShoppingRules)
async def update_rules(rules: ShoppingRules) -> ShoppingRules:
    """Replace all shopping rules."""
    await _rules_manager.save_rules(rules)
    return rules


@router.patch("/avoid", response_model=ShoppingRules)
async def update_avoid_rules(avoid: list[AvoidRule]) -> ShoppingRules:
    """Update the avoid-items list."""
    return await _rules_manager.update_avoid(avoid)


@router.patch("/brands", response_model=ShoppingRules)
async def update_brand_rules(brands: list[BrandRule]) -> ShoppingRules:
    """Update brand preference rules."""
    return await _rules_manager.update_brands(brands)


@router.patch("/preferences", response_model=ShoppingRules)
async def update_price_preferences(price: PricePreference) -> ShoppingRules:
    """Update price strategy preferences."""
    return await _rules_manager.update_preferences(price)
