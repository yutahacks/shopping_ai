import asyncio
from pathlib import Path
import yaml

from app.config import settings
from app.models.rules import AvoidRule, BrandRule, PricePreference, ShoppingRules


class RulesManagerService:
    def __init__(self, rules_path: Path | None = None) -> None:
        self._path = rules_path or settings.rules_path
        self._lock = asyncio.Lock()

    async def get_rules(self) -> ShoppingRules:
        async with self._lock:
            return await asyncio.to_thread(self._read_rules)

    async def save_rules(self, rules: ShoppingRules) -> None:
        async with self._lock:
            await asyncio.to_thread(self._write_rules, rules)

    async def update_avoid(self, avoid: list[AvoidRule]) -> ShoppingRules:
        rules = await self.get_rules()
        rules.avoid = avoid
        await self.save_rules(rules)
        return rules

    async def update_brands(self, brands: list[BrandRule]) -> ShoppingRules:
        rules = await self.get_rules()
        rules.brands = brands
        await self.save_rules(rules)
        return rules

    async def update_preferences(self, price: PricePreference) -> ShoppingRules:
        rules = await self.get_rules()
        rules.price = price
        await self.save_rules(rules)
        return rules

    def _read_rules(self) -> ShoppingRules:
        if not self._path.exists():
            return ShoppingRules()
        with open(self._path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return ShoppingRules.model_validate(data)

    def _write_rules(self, rules: ShoppingRules) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = rules.model_dump(exclude_none=True)
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
