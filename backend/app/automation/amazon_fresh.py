"""Amazon Fresh Japan automation.

IMPORTANT: This automator NEVER navigates to checkout or purchase pages.
It only searches for products and adds them to the cart.
"""

import re
from dataclasses import dataclass

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.automation.selectors import AmazonFreshSelectors as S
from app.models.cart import CartItemResult
from app.models.rules import ShoppingRules

AMAZON_FRESH_URL = "https://www.amazon.co.jp/alm/storefront?almBrandId=QW1hem9uIEZyZXNo"
AMAZON_SEARCH_URL = "https://www.amazon.co.jp/s?k={query}&i=amazonfresh"


@dataclass
class ProductCandidate:
    title: str
    price: int | None
    asin: str | None
    element_index: int


class AmazonFreshAutomator:
    """Automates Amazon Fresh Japan product search and cart addition.

    Never navigates to checkout or purchase pages.
    """

    def __init__(self, page: Page, rules: ShoppingRules) -> None:
        self._page = page
        self._rules = rules

    async def check_login_status(self) -> bool:
        """Check if the user is logged in by inspecting the account nav."""
        try:
            await self._page.goto("https://www.amazon.co.jp/", wait_until="domcontentloaded")
            account_text = await self._page.text_content(S.NAV_ACCOUNT)
            if account_text:
                # If not logged in, text contains "ログイン" (Sign in)
                return "ログイン" not in account_text
        except Exception:
            pass
        return False

    async def search_and_add_to_cart(self, item_name: str, quantity: str) -> CartItemResult:
        """Search for an item and add it to the cart.

        Args:
            item_name: Product name to search for.
            quantity: Quantity string (for display only; cart addition is one unit).

        Returns:
            CartItemResult with the outcome.
        """
        try:
            candidates = await self._search_products(item_name)
            if not candidates:
                return CartItemResult(
                    item_name=item_name,
                    status="not_found",
                    error_message=f"'{item_name}'の検索結果が見つかりませんでした",
                )

            selected = self._select_best_product(candidates)
            if selected is None:
                return CartItemResult(
                    item_name=item_name,
                    status="not_found",
                    error_message="ルールに合う商品が見つかりませんでした",
                )

            success = await self._add_to_cart(selected.element_index)
            if success:
                return CartItemResult(
                    item_name=item_name,
                    status="added",
                    product_found=selected.title,
                    price=selected.price,
                    asin=selected.asin,
                )
            else:
                return CartItemResult(
                    item_name=item_name,
                    status="error",
                    product_found=selected.title,
                    error_message="カートへの追加に失敗しました",
                )

        except PlaywrightTimeoutError:
            return CartItemResult(
                item_name=item_name,
                status="error",
                error_message="タイムアウト: ページの読み込みに時間がかかりすぎました",
            )
        except Exception as e:
            return CartItemResult(
                item_name=item_name,
                status="error",
                error_message=str(e),
            )

    async def _search_products(self, query: str) -> list[ProductCandidate]:
        """Search Amazon Fresh and return product candidates."""
        url = AMAZON_SEARCH_URL.format(query=query.replace(" ", "+"))
        await self._page.goto(url, wait_until="domcontentloaded")

        try:
            await self._page.wait_for_selector(S.SEARCH_RESULTS, timeout=10000)
        except PlaywrightTimeoutError:
            return []

        results = await self._page.query_selector_all(S.SEARCH_RESULTS)
        candidates: list[ProductCandidate] = []

        for idx, result in enumerate(results[:10]):  # Check top 10 results
            try:
                title_el = await result.query_selector(S.PRODUCT_TITLE)
                if not title_el:
                    continue
                title = (await title_el.text_content() or "").strip()

                price_el = await result.query_selector(S.PRODUCT_PRICE)
                price: int | None = None
                if price_el:
                    price_text = await price_el.text_content() or ""
                    price = self._parse_price(price_text)

                # Extract ASIN from data attribute
                asin = await result.get_attribute("data-asin")

                candidates.append(
                    ProductCandidate(
                        title=title,
                        price=price,
                        asin=asin,
                        element_index=idx,
                    )
                )
            except Exception:
                continue

        return candidates

    def _select_best_product(self, candidates: list[ProductCandidate]) -> ProductCandidate | None:
        """Apply brand and price rules to select the best product."""
        if not candidates:
            return None

        # Apply brand rules
        brand_filtered = self._apply_brand_rules(candidates)
        pool = brand_filtered if brand_filtered else candidates

        # Filter by max price
        if self._rules.price.max_price_per_item is not None:
            pool = [
                c
                for c in pool
                if c.price is None or c.price <= self._rules.price.max_price_per_item
            ]
            if not pool:
                pool = candidates  # fallback

        # Apply price strategy
        return self._apply_price_strategy(pool)

    def _apply_brand_rules(self, candidates: list[ProductCandidate]) -> list[ProductCandidate]:
        """Filter candidates by brand rules if applicable."""
        preferred: list[ProductCandidate] = []
        for rule in self._rules.brands:
            for candidate in candidates:
                if rule.brand.lower() in candidate.title.lower():
                    preferred.append(candidate)
        return preferred

    def _apply_price_strategy(self, candidates: list[ProductCandidate]) -> ProductCandidate | None:
        """Select based on price strategy."""
        priced = [c for c in candidates if c.price is not None]
        unpriced = [c for c in candidates if c.price is None]

        strategy = self._rules.price.strategy

        if strategy == "cheapest":
            if priced:
                return min(priced, key=lambda c: c.price)  # type: ignore[return-value]
            return unpriced[0] if unpriced else None

        elif strategy == "premium":
            if priced:
                return max(priced, key=lambda c: c.price)  # type: ignore[return-value]
            return unpriced[0] if unpriced else None

        else:  # value: pick middle
            if priced:
                sorted_priced = sorted(priced, key=lambda c: c.price)  # type: ignore[arg-type]
                mid = len(sorted_priced) // 2
                return sorted_priced[mid]
            return unpriced[0] if unpriced else None

    async def _add_to_cart(self, result_index: int) -> bool:
        """Click the add-to-cart button for the result at the given index."""
        results = await self._page.query_selector_all(S.SEARCH_RESULTS)
        if result_index >= len(results):
            return False

        result = results[result_index]

        # Try inline add-to-cart button first
        add_btn = await result.query_selector(S.ADD_TO_CART_BUTTON)
        if add_btn:
            await add_btn.click()
            await self._page.wait_for_timeout(1000)
            return True

        # Navigate to product page and add from there
        title_link = await result.query_selector("h2 a")
        if not title_link:
            return False

        product_url = await title_link.get_attribute("href")
        if not product_url:
            return False

        if not product_url.startswith("http"):
            product_url = f"https://www.amazon.co.jp{product_url}"

        # Safety check: never navigate to checkout pages
        forbidden_paths = ["/checkout", "/buy", "/order", "/purchase", "/payment"]
        if any(path in product_url for path in forbidden_paths):
            return False

        await self._page.goto(product_url, wait_until="domcontentloaded")

        try:
            await self._page.wait_for_selector(S.ADD_TO_CART_SUBMIT, timeout=5000)
            await self._page.click(S.ADD_TO_CART_SUBMIT)
            await self._page.wait_for_timeout(1500)
            return True
        except PlaywrightTimeoutError:
            return False

    @staticmethod
    def _parse_price(price_text: str) -> int | None:
        """Parse a price string like '¥298' or '298円' into an integer."""
        cleaned = re.sub(r"[^\d]", "", price_text)
        if cleaned:
            return int(cleaned)
        return None
