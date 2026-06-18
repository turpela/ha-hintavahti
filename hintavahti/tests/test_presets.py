"""Yksikkötestit presets.py:lle ja presettien yhteistyölle scraper.py:n kanssa."""
from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from app.presets import get_preset_selectors
from app.scraper import _price_from_selector


# ---------------------------------------------------------------------------
# get_preset_selectors – URL-kohdistus
# ---------------------------------------------------------------------------

class TestGetPresetSelectors:
    def test_jysk_fi(self):
        assert get_preset_selectors("https://jysk.fi/olohuone/sohvat/tuote") != []

    def test_jysk_fi_www(self):
        assert get_preset_selectors("https://www.jysk.fi/tuote") != []

    def test_verkkokauppa(self):
        assert get_preset_selectors("https://www.verkkokauppa.com/tuote") != []

    def test_unknown_domain(self):
        assert get_preset_selectors("https://example.com/tuote") == []

    def test_subdomain_match(self):
        # sub.gigantti.fi pitäisi matchata gigantti.fi
        assert get_preset_selectors("https://sub.gigantti.fi/tuote") != []


# ---------------------------------------------------------------------------
# JYSK-presetti – bugikorjaus alennusbadgelle
# ---------------------------------------------------------------------------

class TestJyskPreset:
    """Varmistaa että JYSK:n alennusbadge (-31%) ei enää mene hinnaksi."""

    def _soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    def test_jysk_sale_price_not_discount_badge(self):
        """Alennussivu: .product-price-value löytää 550, ei 31."""
        html = """
        <div class="pdp-product-price">
          <span class="product-label__percentage">-31%</span>
          <div class="product-price-wrapper">
            <div class="product-price discountprice text-bold">
              <span class="product-price-value">550,-</span>
              <span class="unit product-price-unit">/kpl</span>
            </div>
          </div>
        </div>
        """
        soup = self._soup(html)
        selectors = get_preset_selectors("https://jysk.fi/tuote")
        assert selectors, "JYSK-presettiä ei löydy"

        price = None
        for sel in selectors:
            price = _price_from_selector(soup, sel)
            if price is not None:
                break

        assert price == 550.0, f"Odotettu 550.0, saatiin {price}"

    def test_jysk_old_selector_not_in_presets(self):
        """Vanhentunut .product-price__price ei enää ole preseteissä."""
        selectors = get_preset_selectors("https://jysk.fi/tuote")
        assert ".product-price__price" not in selectors

    def test_jysk_no_broad_class_contains_fallback(self):
        """Vaarallinen [class*=\"price\"] ei enää ole JYSK-preseteissä."""
        selectors = get_preset_selectors("https://jysk.fi/tuote")
        assert '[class*="price"]' not in selectors

    def test_jysk_normal_price(self):
        """Normaalihinta (ei alennusta): discountprice-elementistä saadaan oikea hinta."""
        html = """
        <div class="product-price-wrapper">
          <div class="product-price text-bold">
            <span class="product-price-value">799,-</span>
          </div>
        </div>
        """
        soup = self._soup(html)
        price = _price_from_selector(soup, ".product-price-value")
        assert price == 799.0
