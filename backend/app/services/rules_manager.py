"""Service for managing user-defined shopping rules.

Handles CRUD operations for shopping rules stored as YAML files,
including avoidance rules, brand preferences, and price strategies.
"""

import asyncio
from pathlib import Path

import yaml

from app.config import settings
from app.models.rules import AvoidRule, BrandRule, PricePreference, ShoppingRules


class RulesManagerService:
    """Manages shopping rules persisted in a YAML file.

    Attributes:
        _path: Path to the YAML rules file.
        _lock: Async lock for thread-safe file access.
    """

    def __init__(self, rules_path: Path | None = None) -> None:
        """Initializes the rules manager.

        Args:
            rules_path: Optional path to the rules YAML file.
                Falls back to the configured default path.
        """
        self._path = rules_path or settings.rules_path
        self._lock = asyncio.Lock()

    async def get_rules(self) -> ShoppingRules:
        """Loads and returns shopping rules from the YAML file.

        Returns:
            The current shopping rules, or defaults if no file exists.
        """
        async with self._lock:
            return await asyncio.to_thread(self._read_rules)

    async def save_rules(self, rules: ShoppingRules) -> None:
        """Persists shopping rules to the YAML file.

        Args:
            rules: The shopping rules to save.
        """
        async with self._lock:
            await asyncio.to_thread(self._write_rules, rules)

    async def update_avoid(self, avoid: list[AvoidRule]) -> ShoppingRules:
        """Replaces the avoidance rules and saves.

        Args:
            avoid: New list of avoidance rules.

        Returns:
            The updated shopping rules.
        """
        rules = await self.get_rules()
        rules.avoid = avoid
        await self.save_rules(rules)
        return rules

    async def update_brands(self, brands: list[BrandRule]) -> ShoppingRules:
        """Replaces the brand preference rules and saves.

        Args:
            brands: New list of brand preference rules.

        Returns:
            The updated shopping rules.
        """
        rules = await self.get_rules()
        rules.brands = brands
        await self.save_rules(rules)
        return rules

    async def update_preferences(self, price: PricePreference) -> ShoppingRules:
        """Replaces the price preference and saves.

        Args:
            price: New price preference settings.

        Returns:
            The updated shopping rules.
        """
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
