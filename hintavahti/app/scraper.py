"""Fetch a product page and extract its price.

Two fetch backends:
  * httpx  - fast, no browser, works when the price is in the initial HTML.
  * Playwright (Chromium) - renders JavaScript, for shops that load the price
    dynamically. Used when a product is flagged use_js, or available as an
    explicit choice. Imported lazily so the app still runs if Playwright or the
    browser is not installed.

Price detection order on the fetched HTML:
  1. user-supplied CSS selector
  2. JSON-LD structured product data
  3. per-shop preset selectors (presets.py)
  4. common meta tags
"""
from __future__ import annotations

import json
import logging
import re

import httpx
from bs4 import BeautifulSoup

from . import config, presets

log = logging.getLogger("hintavahti.scraper")


class PriceError(Exception):
    """Raised when a price could not be determined."""


_NUMBER_RE = re.compile(r"[\d][\d.,\s\u00a0]*\d|\d")


def parse_price(text: str | None) -> float | None:
    if text is None:
        return None
    text = str(text).strip()
    if not text:
        return None
    match = _NUMBER_RE.search(text)
    if not match:
        return None
    num = match.group(0).replace("\u00a0", "").replace(" ", "")

    has_comma, has_dot = "," in num, "." in num
    if has_comma and has_dot:
        if num.rfind(",") > num.rfind("."):
            num = num.replace(".", "").replace(",", ".")
        else:
            num = num.replace(",", "")
    elif has_comma:
        if re.search(r",\d{1,2}$", num):
            num = num.replace(",", ".")
        else:
            num = num.replace(",", "")

    try:
        value = float(num)
    except ValueError:
        return None
    return value if value > 0 else None


def _walk_jsonld_for_price(node) -> list:
    found: list = []
    if isinstance(node, dict):
        for key in ("price", "lowPrice", "highPrice"):
            if node.get(key) not in (None, ""):
                found.append(node[key])
        for value in node.values():
            found.extend(_walk_jsonld_for_price(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_walk_jsonld_for_price(item))
    return found


def _price_from_jsonld(soup: BeautifulSoup) -> float | None:
    for tag in soup.find_all("script", type="application/ld+json"):
        raw = tag.string or tag.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        for price in _walk_jsonld_for_price(data):
            parsed = parse_price(price)
            if parsed is not None:
                return parsed
    return None


def _price_from_meta(soup: BeautifulSoup) -> float | None:
    for attr, value in (
        ("property", "product:price:amount"),
        ("property", "og:price:amount"),
        ("itemprop", "price"),
    ):
        tag = soup.find("meta", attrs={attr: value})
        if tag and tag.get("content"):
            parsed = parse_price(tag["content"])
            if parsed is not None:
                return parsed
    el = soup.find(attrs={"itemprop": "price"})
    if el:
        parsed = parse_price(el.get("content") or el.get_text())
        if parsed is not None:
            return parsed
    return None


def _price_from_selector(soup: BeautifulSoup, selector: str) -> float | None:
    el = soup.select_one(selector)
    if not el:
        return None
    return parse_price(el.get("content") or el.get_text())


def _price_from_presets(soup: BeautifulSoup, url: str) -> float | None:
    for selector in presets.get_preset_selectors(url):
        price = _price_from_selector(soup, selector)
        if price is not None:
            return price
    return None


# --- Fetch backends -------------------------------------------------------
def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": config.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fi-FI,fi;q=0.9,en;q=0.8",
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=20.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def playwright_available() -> bool:
    if not config.PLAYWRIGHT_ENABLED:
        return False
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except ImportError:
        return False


def fetch_html_js(url: str) -> str:
    """Render the page with Chromium and return the resulting HTML.

    Runs the synchronous Playwright API; this is safe here because checks run
    in worker threads, not inside the asyncio event loop.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise PriceError(
            "JS-renderöinti ei ole käytettävissä (Playwright puuttuu)."
        ) from exc

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--no-sandbox"])
            try:
                page = browser.new_page(
                    user_agent=config.USER_AGENT, locale="fi-FI"
                )
                page.goto(
                    url, wait_until="networkidle", timeout=config.PLAYWRIGHT_TIMEOUT_MS
                )
                return page.content()
            finally:
                browser.close()
    except PriceError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface a readable message
        raise PriceError(f"JS-renderöinti epäonnistui: {exc}") from exc


# --- Public API -----------------------------------------------------------
def get_price(url: str, css_selector: str = "", use_js: bool = False) -> float:
    """Fetch the page and return the detected price, or raise PriceError."""
    try:
        html = fetch_html_js(url) if use_js else fetch_html(url)
    except PriceError:
        raise
    except httpx.HTTPStatusError as exc:
        raise PriceError(f"Sivu vastasi virhekoodilla {exc.response.status_code}")
    except httpx.HTTPError as exc:
        raise PriceError(f"Sivun haku epäonnistui: {exc}")

    soup = BeautifulSoup(html, "lxml")

    if css_selector:
        price = _price_from_selector(soup, css_selector)
        if price is not None:
            return price
        raise PriceError("Annettu CSS-valitsin ei tuottanut hintaa.")

    for finder in (
        lambda s: _price_from_jsonld(s),
        lambda s: _price_from_presets(s, url),
        lambda s: _price_from_meta(s),
    ):
        price = finder(soup)
        if price is not None:
            return price

    if not use_js:
        raise PriceError(
            "Hintaa ei tunnistettu. Kokeile ottaa käyttöön JS-renderöinti "
            "tai lisää CSS-valitsin."
        )
    raise PriceError(
        "Hintaa ei tunnistettu edes JS-renderöinnillä. Lisää CSS-valitsin."
    )
