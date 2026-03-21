"""Global semaphore to limit concurrent browser instances.

Prevents memory exhaustion from too many simultaneous Playwright
browser processes.
"""

import asyncio

# Maximum concurrent browser instances
_browser_semaphore = asyncio.Semaphore(2)


def get_browser_semaphore() -> asyncio.Semaphore:
    """Return the global browser semaphore."""
    return _browser_semaphore
