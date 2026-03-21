"""Unit tests for AmazonFreshAutomator — static methods and product selection."""

import pytest

from app.automation.amazon_fresh import AmazonFreshAutomator, ProductCandidate
from app.models.rules import BrandRule, PricePreference, ShoppingRules


@pytest.fixture
def default_rules() -> ShoppingRules:
    """Create default shopping rules for testing."""
    return ShoppingRules()


@pytest.fixture
def brand_rules() -> ShoppingRules:
    """Create rules with brand preferences."""
    return ShoppingRules(
        brands=[
            BrandRule(product_pattern="シャンプー", brand="パンテーン"),
            BrandRule(product_pattern="牛乳", brand="明治"),
        ],
    )


class TestParsePrice:
    """Tests for price parsing."""

    def test_yen_symbol(self) -> None:
        assert AmazonFreshAutomator._parse_price("¥298") == 298

    def test_en_suffix(self) -> None:
        assert AmazonFreshAutomator._parse_price("298円") == 298

    def test_comma_separated(self) -> None:
        assert AmazonFreshAutomator._parse_price("¥1,298") == 1298

    def test_empty(self) -> None:
        assert AmazonFreshAutomator._parse_price("") is None

    def test_no_digits(self) -> None:
        assert AmazonFreshAutomator._parse_price("価格なし") is None


class TestParseQuantity:
    """Tests for quantity parsing."""

    def test_count_unit(self) -> None:
        assert AmazonFreshAutomator._parse_quantity("2個") == 2

    def test_pack_unit(self) -> None:
        assert AmazonFreshAutomator._parse_quantity("3パック") == 3

    def test_bag_unit(self) -> None:
        assert AmazonFreshAutomator._parse_quantity("1袋") == 1

    def test_weight_grams(self) -> None:
        # Weight → 1 (buy one package)
        assert AmazonFreshAutomator._parse_quantity("300g") == 1

    def test_weight_kg(self) -> None:
        assert AmazonFreshAutomator._parse_quantity("1kg") == 1

    def test_volume_ml(self) -> None:
        assert AmazonFreshAutomator._parse_quantity("500ml") == 1

    def test_no_match(self) -> None:
        assert AmazonFreshAutomator._parse_quantity("適量") == 1

    def test_zero_defaults_to_one(self) -> None:
        assert AmazonFreshAutomator._parse_quantity("0個") == 1


class TestExtractSpecKeywords:
    """Tests for spec keyword extraction from quantity strings."""

    def test_parenthesized_count(self) -> None:
        assert AmazonFreshAutomator._extract_spec_keywords("1パック（10個）") == ["10個"]

    def test_parenthesized_volume(self) -> None:
        assert AmazonFreshAutomator._extract_spec_keywords("2本（1L）") == ["1L"]

    def test_standalone_weight(self) -> None:
        assert AmazonFreshAutomator._extract_spec_keywords("800g") == ["800g"]

    def test_plain_count_no_spec(self) -> None:
        # "3袋" has no spec info, just count
        assert AmazonFreshAutomator._extract_spec_keywords("3袋") == []

    def test_multiple_specs(self) -> None:
        result = AmazonFreshAutomator._extract_spec_keywords("1パック（900g）")
        assert "900g" in result


class TestSelectBestProduct:
    """Tests for product selection logic."""

    def _make_candidates(self) -> list[ProductCandidate]:
        return [
            ProductCandidate(title="商品A 安い", price=100, asin="A1", element_index=0),
            ProductCandidate(title="商品B 中間", price=300, asin="A2", element_index=1),
            ProductCandidate(title="商品C 高い", price=500, asin="A3", element_index=2),
        ]

    def test_cheapest_strategy(self, default_rules: ShoppingRules) -> None:
        # default is cheapest
        automator = AmazonFreshAutomator.__new__(AmazonFreshAutomator)
        automator._rules = default_rules
        result = automator._select_best_product(self._make_candidates())
        assert result is not None
        assert result.price == 100

    def test_premium_strategy(self) -> None:
        rules = ShoppingRules(price=PricePreference(strategy="premium"))
        automator = AmazonFreshAutomator.__new__(AmazonFreshAutomator)
        automator._rules = rules
        result = automator._select_best_product(self._make_candidates())
        assert result is not None
        assert result.price == 500

    def test_value_strategy(self) -> None:
        rules = ShoppingRules(price=PricePreference(strategy="value"))
        automator = AmazonFreshAutomator.__new__(AmazonFreshAutomator)
        automator._rules = rules
        result = automator._select_best_product(self._make_candidates())
        assert result is not None
        assert result.price == 300

    def test_max_price_filter(self) -> None:
        rules = ShoppingRules(price=PricePreference(strategy="premium", max_price_per_item=400))
        automator = AmazonFreshAutomator.__new__(AmazonFreshAutomator)
        automator._rules = rules
        result = automator._select_best_product(self._make_candidates())
        assert result is not None
        assert result.price == 300  # C is filtered out

    def test_empty_candidates(self, default_rules: ShoppingRules) -> None:
        automator = AmazonFreshAutomator.__new__(AmazonFreshAutomator)
        automator._rules = default_rules
        assert automator._select_best_product([]) is None

    def test_brand_rule_category_match(self, brand_rules: ShoppingRules) -> None:
        """Brand rules only apply when item name matches the product pattern."""
        candidates = [
            ProductCandidate(
                title="パンテーン シャンプー 400ml",
                price=500,
                asin="A1",
                element_index=0,
            ),
            ProductCandidate(
                title="いち髪 シャンプー 380ml",
                price=300,
                asin="A2",
                element_index=1,
            ),
        ]
        automator = AmazonFreshAutomator.__new__(AmazonFreshAutomator)
        automator._rules = brand_rules
        # When searching for "シャンプー", brand rule should match
        result = automator._select_best_product(
            candidates,
            item_name="シャンプー",
        )
        assert result is not None
        assert "パンテーン" in result.title

    def test_frozen_exclusion(self, default_rules: ShoppingRules) -> None:
        """Frozen products are excluded unless explicitly requested."""
        candidates = [
            ProductCandidate(title="冷凍 豚こま切れ肉 800g", price=500, asin="A1", element_index=0),
            ProductCandidate(title="豚こま切れ肉 800g", price=600, asin="A2", element_index=1),
        ]
        automator = AmazonFreshAutomator.__new__(AmazonFreshAutomator)
        automator._rules = default_rules
        result = automator._select_best_product(candidates, item_name="豚こま切れ肉")
        assert result is not None
        assert "冷凍" not in result.title

    def test_frozen_included_when_requested(self, default_rules: ShoppingRules) -> None:
        """Frozen products are kept when item name includes 冷凍."""
        candidates = [
            ProductCandidate(title="冷凍 豚こま切れ肉 800g", price=500, asin="A1", element_index=0),
            ProductCandidate(title="豚こま切れ肉 800g", price=600, asin="A2", element_index=1),
        ]
        automator = AmazonFreshAutomator.__new__(AmazonFreshAutomator)
        automator._rules = default_rules
        result = automator._select_best_product(candidates, item_name="冷凍豚こま切れ肉")
        assert result is not None
        assert result.price == 500  # cheapest, frozen is allowed

    def test_spec_keyword_filtering(self, default_rules: ShoppingRules) -> None:
        """Products matching spec keywords from quantity are preferred."""
        candidates = [
            ProductCandidate(title="明治 牛乳 450ml", price=200, asin="A1", element_index=0),
            ProductCandidate(title="明治 牛乳 1L", price=300, asin="A2", element_index=1),
            ProductCandidate(title="明治 牛乳 200ml", price=100, asin="A3", element_index=2),
        ]
        automator = AmazonFreshAutomator.__new__(AmazonFreshAutomator)
        automator._rules = default_rules
        result = automator._select_best_product(
            candidates, item_name="牛乳", quantity_raw="2本（1L）"
        )
        assert result is not None
        assert "1L" in result.title

    def test_spec_keyword_egg_count(self, default_rules: ShoppingRules) -> None:
        """Egg count spec is respected."""
        candidates = [
            ProductCandidate(title="たまご 6個入り", price=200, asin="A1", element_index=0),
            ProductCandidate(title="たまご 10個入り", price=300, asin="A2", element_index=1),
        ]
        automator = AmazonFreshAutomator.__new__(AmazonFreshAutomator)
        automator._rules = default_rules
        result = automator._select_best_product(
            candidates, item_name="卵", quantity_raw="1パック（10個）"
        )
        assert result is not None
        assert "10個" in result.title

    def test_brand_rule_no_category_match(self, brand_rules: ShoppingRules) -> None:
        """Brand rules don't apply when item name doesn't match product pattern."""
        candidates = [
            ProductCandidate(
                title="パンテーン シャンプー 400ml",
                price=500,
                asin="A1",
                element_index=0,
            ),
            ProductCandidate(
                title="いち髪 シャンプー 380ml",
                price=300,
                asin="A2",
                element_index=1,
            ),
        ]
        automator = AmazonFreshAutomator.__new__(AmazonFreshAutomator)
        automator._rules = brand_rules
        # When searching for "洗剤", brand rule for シャンプー shouldn't apply
        result = automator._select_best_product(candidates, item_name="洗剤")
        assert result is not None
        # Should pick cheapest (default strategy) since brand rule doesn't apply
        assert result.price == 300
