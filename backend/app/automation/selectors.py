"""CSS selectors for Amazon Fresh Japan pages.

Centralizes all DOM selectors so that changes to Amazon's HTML
structure only require edits in one place.
"""


class AmazonFreshSelectors:
    """CSS selectors for Amazon Fresh Japan page elements.

    All attributes are class-level string constants representing CSS
    selectors for search, product, cart, login, and pagination elements.
    """

    # Search
    SEARCH_BOX = "#twotabsearchtextbox"
    SEARCH_BUTTON = "#nav-search-submit-button"

    # Product listings
    SEARCH_RESULTS = "[data-component-type='s-search-result']"
    PRODUCT_TITLE = "h2 .a-text-normal"
    PRODUCT_PRICE = ".a-price .a-offscreen"
    ADD_TO_CART_BUTTON = "[data-action='add-to-cart']"
    ADD_TO_CART_SUBMIT = "#add-to-cart-button"

    # Product page
    PRODUCT_TITLE_PAGE = "#productTitle"
    PRODUCT_PRICE_PAGE = ".a-price.aok-align-center .a-offscreen"

    # Cart
    CART_ICON = "#nav-cart"
    CART_COUNT = "#nav-cart-count"

    # Login detection
    NAV_ACCOUNT = "#nav-link-accountList"
    SIGN_IN_FORM = "#ap_email"

    # Fresh-specific
    FRESH_BADGE = "[aria-label*='Amazon Fresh']"
    DELIVERY_AVAILABLE = ".a-color-success"

    # Quantity controls
    QUANTITY_SELECT = "select[id*='quantity']"
    QUANTITY_INPUT = "input[id*='quantity']"
    QUANTITY_SELECT_PDP = "#quantity"

    # Pagination
    NEXT_PAGE = ".s-pagination-next:not(.s-pagination-disabled)"
