"""Amazon Fresh Japan automation.

IMPORTANT: This automator NEVER navigates to checkout or purchase pages.
It only searches for products and adds them to the cart.
"""

import logging
import re
from dataclasses import dataclass

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.automation.selectors import AmazonFreshSelectors as S
from app.models.cart import CartItemResult
from app.models.rules import ShoppingRules

logger = logging.getLogger(__name__)

AMAZON_FRESH_URL = "https://www.amazon.co.jp/alm/storefront?almBrandId=QW1hem9uIEZyZXNo"
AMAZON_SEARCH_URL = "https://www.amazon.co.jp/s?k={query}&i=amazonfresh"

MAX_RETRIES = 2


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
                logged_in = "ログイン" not in account_text
                logger.info("Login status check: %s", "logged in" if logged_in else "not logged in")
                return logged_in
        except Exception:
            logger.exception("Failed to check login status")
        return False

    async def search_and_add_to_cart(self, item_name: str, quantity: str) -> CartItemResult:
        """Search for an item and add it to the cart.

        Args:
            item_name: Product name to search for.
            quantity: Quantity string (e.g., "2個", "300g").

        Returns:
            CartItemResult with the outcome.
        """
        parsed_qty = self._parse_quantity(quantity)
        logger.info("Processing item: %s (quantity: %s, parsed: %d)", item_name, quantity, parsed_qty)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = await self._try_search_and_add(item_name, parsed_qty)
                if result.status != "error" or attempt == MAX_RETRIES:
                    return result
                logger.warning(
                    "Attempt %d/%d failed for '%s': %s. Retrying...",
                    attempt, MAX_RETRIES, item_name, result.error_message,
                )
            except PlaywrightTimeoutError:
                logger.warning(
                    "Attempt %d/%d timed out for '%s'",
                    attempt, MAX_RETRIES, item_name,
                )
                if attempt == MAX_RETRIES:
                    return CartItemResult(
                        item_name=item_name,
                        status="error",
                        error_message="タイムアウト: ページの読み込みに時間がかかりすぎました",
                    )
            except Exception as e:
                logger.exception(
                    "Attempt %d/%d unexpected error for '%s'",
                    attempt, MAX_RETRIES, item_name,
                )
                if attempt == MAX_RETRIES:
                    return CartItemResult(
                        item_name=item_name,
                        status="error",
                        error_message=str(e),
                    )

        # Should not reach here, but just in case
        return CartItemResult(
            item_name=item_name,
            status="error",
            error_message="リトライ回数を超過しました",
        )

    async def _try_search_and_add(self, item_name: str, quantity: int) -> CartItemResult:
        """Single attempt to search and add an item."""
        candidates = await self._search_products(item_name)
        if not candidates:
            return CartItemResult(
                item_name=item_name,
                status="not_found",
                error_message=f"'{item_name}'の検索結果が見つかりませんでした",
            )

        selected = self._select_best_product(candidates, item_name)
        if selected is None:
            return CartItemResult(
                item_name=item_name,
                status="not_found",
                error_message="ルールに合う商品が見つかりませんでした",
            )

        logger.info("Selected product: %s (¥%s)", selected.title, selected.price)

        success = await self._add_to_cart(selected.element_index, quantity)
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

    async def _search_products(self, query: str) -> list[ProductCandidate]:
        """Search Amazon Fresh and return product candidates."""
        url = AMAZON_SEARCH_URL.format(query=query.replace(" ", "+"))
        logger.debug("Searching: %s", url)
        await self._page.goto(url, wait_until="domcontentloaded")

        try:
            await self._page.wait_for_selector(S.SEARCH_RESULTS, timeout=10000)
        except PlaywrightTimeoutError:
            logger.warning("No search results found for '%s'", query)
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
                logger.debug("Failed to parse search result at index %d", idx)
                continue

        logger.info("Found %d candidates for '%s'", len(candidates), query)
        return candidates

    def _select_best_product(
        self, candidates: list[ProductCandidate], item_name: str = ""
    ) -> ProductCandidate | None:
        """Apply brand and price rules to select the best product."""
        if not candidates:
            return None

        # Apply brand rules (with category matching)
        brand_filtered = self._apply_brand_rules(candidates, item_name)
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

    def _apply_brand_rules(
        self, candidates: list[ProductCandidate], item_name: str = ""
    ) -> list[ProductCandidate]:
        """Filter candidates by brand rules if the item matches the product pattern."""
        preferred: list[ProductCandidate] = []
        for rule in self._rules.brands:
            # Check if the item_name or search query matches the product_pattern (category)
            if rule.product_pattern.lower() not in item_name.lower():
                continue
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

    async def _add_to_cart(self, result_index: int, quantity: int = 1) -> bool:
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
            # Set quantity if > 1
            if quantity > 1:
                await self._set_quantity(quantity)
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
            logger.warning("Blocked navigation to forbidden URL: %s", product_url)
            return False

        await self._page.goto(product_url, wait_until="domcontentloaded")

        # Set quantity on product page if > 1
        if quantity > 1:
            await self._set_quantity_on_product_page(quantity)

        try:
            await self._page.wait_for_selector(S.ADD_TO_CART_SUBMIT, timeout=5000)
            await self._page.click(S.ADD_TO_CART_SUBMIT)
            await self._page.wait_for_timeout(1500)
            return True
        except PlaywrightTimeoutError:
            logger.warning("Add-to-cart button not found on product page")
            return False

    async def _set_quantity(self, quantity: int) -> None:
        """Try to set the quantity using the quantity dropdown/select."""
        try:
            qty_select = await self._page.query_selector(S.QUANTITY_SELECT)
            if qty_select:
                await qty_select.select_option(str(quantity))
                logger.info("Set quantity to %d via dropdown", quantity)
                await self._page.wait_for_timeout(500)
                return

            # Try the quantity input field as fallback
            qty_input = await self._page.query_selector(S.QUANTITY_INPUT)
            if qty_input:
                await qty_input.fill(str(quantity))
                logger.info("Set quantity to %d via input", quantity)
                await self._page.wait_for_timeout(500)
        except Exception:
            logger.debug("Could not set quantity to %d", quantity)

    async def _set_quantity_on_product_page(self, quantity: int) -> None:
        """Set quantity on the product detail page."""
        try:
            qty_select = await self._page.query_selector(S.QUANTITY_SELECT_PDP)
            if qty_select:
                await qty_select.select_option(str(quantity))
                logger.info("Set quantity to %d on product page", quantity)
                await self._page.wait_for_timeout(500)
        except Exception:
            logger.debug("Could not set quantity on product page")

    @staticmethod
    def _parse_quantity(quantity_str: str) -> int:
        """Parse a quantity string like '2個', '3袋', '300g' into a cart quantity.

        For weight-based quantities (g, kg, ml, L), returns 1.
        For count-based quantities, returns the number.
        """
        match = re.match(r"(\d+)\s*(個|袋|本|箱|パック|束|枚|缶|瓶|丁)?", quantity_str)
        if match:
            num = int(match.group(1))
            unit = match.group(2)
            # Weight/volume units → 1 item (the product itself has the weight)
            if unit is None and any(u in quantity_str for u in ("g", "kg", "ml", "L", "リットル")):
                return 1
            return max(1, num)
        return 1

    @staticmethod
    def _parse_price(price_text: str) -> int | None:
        """Parse a price string like '¥298' or '298円' into an integer."""
        cleaned = re.sub(r"[^\d]", "", price_text)
        if cleaned:
            return int(cleaned)
        return None
