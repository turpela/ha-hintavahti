"""Per-domain price selector presets for common Finnish shops.

These are a best-effort fallback used only when the automatic structured-data
detection (JSON-LD / meta tags) does not find a price. Shops change their
markup over time, so treat these as editable starting points: if a shop stops
working, open its product page, find the element that holds the price, and add
or fix its CSS selector here.

Matching is by hostname suffix, so "www.gigantti.fi" matches "gigantti.fi".
Each shop lists several candidate selectors; the first one that yields a
parseable price wins.
"""
from __future__ import annotations

from urllib.parse import urlparse

# domain suffix -> ordered list of candidate CSS selectors
PRESETS: dict[str, list[str]] = {
    "verkkokauppa.com": [
        '[data-test-id="product-price"]',
        '[itemprop="price"]',
        ".price",
    ],
    "gigantti.fi": [
        ".product-price-container .price",
        '[class*="ProductPrice"]',
        '[itemprop="price"]',
    ],
    "power.fi": [
        ".product-price .price-now",
        '[class*="price"]',
        '[itemprop="price"]',
    ],
    "tokmanni.fi": [
        ".product-info-price .price",
        ".price-wrapper .price",
        '[itemprop="price"]',
    ],
    "xxl.fi": [
        ".product-price__now",
        '[class*="price"]',
    ],
    "prisma.fi": [
        '[data-test-id="product-price"]',
        ".product-price",
    ],
    "s-kaupat.fi": [
        '[data-test-id="product-price"]',
        ".product-price",
    ],
    "k-ruoka.fi": [
        '[data-testid="product-price"]',
        '[data-test-id="product-price"]',
        '[class*="price"]',
        '[itemprop="price"]',
    ],
    "motonet.fi": [
        ".product-price",
        '[itemprop="price"]',
    ],
    "biltema.fi": [
        ".product-price",
        '[class*="price"]',
    ],
    "clasohlson.com": [
        ".product-price",
        '[class*="price"]',
    ],
    "jysk.fi": [
        ".product-price__price",
        '[class*="price"]',
    ],
    "ikea.com": [
        ".pip-price__integer",
        '[class*="price"]',
    ],
    "jimms.fi": [
        ".product-price",
        '[itemprop="price"]',
    ],
    "multitronic.fi": [
        ".price",
        '[itemprop="price"]',
    ],
    "proshop.fi": [
        ".price-show",
        '[itemprop="price"]',
    ],
    "karkkainen.com": [
        ".product-price",
        '[itemprop="price"]',
    ],
}


def get_preset_selectors(url: str) -> list[str]:
    """Return candidate selectors for the URL's shop, or an empty list."""
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    for domain, selectors in PRESETS.items():
        if host == domain or host.endswith("." + domain):
            return selectors
    return []
