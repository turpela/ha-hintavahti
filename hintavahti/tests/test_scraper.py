"""Yksikkötestit scraper.py:n hinnan parsinnalle ja tunnistuslogiikalle."""
from __future__ import annotations

import json

import pytest
from bs4 import BeautifulSoup

from app.scraper import (
    PriceError,
    _price_from_jsonld,
    _price_from_meta,
    _price_from_selector,
    parse_price,
)


# ---------------------------------------------------------------------------
# parse_price – lukuformaatit
# ---------------------------------------------------------------------------

class TestParsePrice:
    def test_integer(self):
        assert parse_price("42") == 42.0

    def test_simple_float_dot(self):
        assert parse_price("19.99") == 19.99

    def test_simple_float_comma(self):
        assert parse_price("19,99") == 19.99

    def test_thousands_dot_decimal_comma(self):
        # Eurooppalainen formaatti: 1.299,00
        assert parse_price("1.299,00") == 1299.0

    def test_thousands_comma_decimal_dot(self):
        # Angloamerikkalainen formaatti: 1,299.00
        assert parse_price("1,299.00") == 1299.0

    def test_nbsp_as_thousands(self):
        # Non-breaking space tuhaterotin: 1 299,00
        assert parse_price("1 299,00") == 1299.0

    def test_narrow_nbsp(self):
        assert parse_price("1 299,00") == 1299.0

    def test_price_with_currency_suffix(self):
        assert parse_price("29,90 €") == 29.90

    def test_price_with_currency_prefix(self):
        assert parse_price("€ 29,90") == 29.90

    def test_price_in_sentence(self):
        assert parse_price("Hinta: 149,00 euroa") == 149.0

    def test_zero_returns_none(self):
        assert parse_price("0") is None

    def test_negative_sign_stripped(self):
        # Regex etsii ensimmäisen numeron: "-5,00" → löytää "5,00" → 5.0
        # Miinusmerkki ei ole osa numeroa hinnoissa
        assert parse_price("-5,00") == 5.0

    def test_none_input(self):
        assert parse_price(None) is None

    def test_empty_string(self):
        assert parse_price("") is None

    def test_whitespace_only(self):
        assert parse_price("   ") is None

    def test_no_digits(self):
        assert parse_price("hinta ei löytynyt") is None

    def test_integer_with_thousands_comma(self):
        # 1,000 → 1000 (ei desimaalipilkku, koska perässä 3 numeroa)
        assert parse_price("1,000") == 1000.0

    def test_single_digit(self):
        assert parse_price("5") == 5.0

    def test_large_price(self):
        assert parse_price("9.999,99") == 9999.99

    def test_price_with_dot_decimal_and_trailing_text(self):
        assert parse_price("99.95 alv 0%") == 99.95


# ---------------------------------------------------------------------------
# _price_from_selector
# ---------------------------------------------------------------------------

class TestPriceFromSelector:
    def _soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    def test_text_content(self):
        soup = self._soup('<span class="price">29,90 €</span>')
        assert _price_from_selector(soup, ".price") == 29.90

    def test_content_attribute(self):
        soup = self._soup('<meta itemprop="price" content="49.95">')
        assert _price_from_selector(soup, 'meta[itemprop="price"]') == 49.95

    def test_selector_not_found(self):
        soup = self._soup("<html><body></body></html>")
        assert _price_from_selector(soup, ".nonexistent") is None

    def test_empty_element(self):
        soup = self._soup('<span class="price"></span>')
        assert _price_from_selector(soup, ".price") is None

    def test_nested_selector(self):
        soup = self._soup('<div class="product"><span class="price">12,50</span></div>')
        assert _price_from_selector(soup, ".product .price") == 12.50


# ---------------------------------------------------------------------------
# _price_from_jsonld
# ---------------------------------------------------------------------------

class TestPriceFromJsonLD:
    def _soup_with_jsonld(self, data: dict) -> BeautifulSoup:
        payload = json.dumps(data)
        html = f'<html><head><script type="application/ld+json">{payload}</script></head></html>'
        return BeautifulSoup(html, "lxml")

    def test_simple_product(self):
        soup = self._soup_with_jsonld({
            "@type": "Product",
            "offers": {"@type": "Offer", "price": "29.90"},
        })
        assert _price_from_jsonld(soup) == 29.90

    def test_price_as_number(self):
        soup = self._soup_with_jsonld({"@type": "Product", "offers": {"price": 149}})
        assert _price_from_jsonld(soup) == 149.0

    def test_low_price(self):
        soup = self._soup_with_jsonld({
            "@type": "Product",
            "offers": {"lowPrice": "19.99", "highPrice": "39.99"},
        })
        # lowPrice löytyy ensin
        assert _price_from_jsonld(soup) == 19.99

    def test_nested_offers_list(self):
        soup = self._soup_with_jsonld({
            "@type": "Product",
            "offers": [{"price": "55.00"}, {"price": "65.00"}],
        })
        assert _price_from_jsonld(soup) == 55.0

    def test_no_jsonld(self):
        soup = BeautifulSoup("<html><body><p>Ei JSON-LD:tä</p></body></html>", "lxml")
        assert _price_from_jsonld(soup) is None

    def test_invalid_json_ignored(self):
        html = '<script type="application/ld+json">EI_VALIDIA_JSON</script>'
        soup = BeautifulSoup(html, "lxml")
        assert _price_from_jsonld(soup) is None

    def test_empty_price_string_ignored(self):
        soup = self._soup_with_jsonld({"price": ""})
        assert _price_from_jsonld(soup) is None


# ---------------------------------------------------------------------------
# _price_from_meta
# ---------------------------------------------------------------------------

class TestPriceFromMeta:
    def _soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    def test_og_price_amount(self):
        soup = self._soup('<meta property="og:price:amount" content="39.90">')
        assert _price_from_meta(soup) == 39.90

    def test_product_price_amount(self):
        soup = self._soup('<meta property="product:price:amount" content="12,50">')
        assert _price_from_meta(soup) == 12.50

    def test_itemprop_meta(self):
        soup = self._soup('<meta itemprop="price" content="99.00">')
        assert _price_from_meta(soup) == 99.0

    def test_itemprop_element(self):
        soup = self._soup('<span itemprop="price">24,90 €</span>')
        assert _price_from_meta(soup) == 24.90

    def test_no_meta(self):
        soup = self._soup("<html><body><p>Ei metatageja</p></body></html>")
        assert _price_from_meta(soup) is None

    def test_empty_content_ignored(self):
        soup = self._soup('<meta property="og:price:amount" content="">')
        assert _price_from_meta(soup) is None
