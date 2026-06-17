"""Yksikkötestit notifier.py:n tekstin siivous- ja apufunktioille."""
from __future__ import annotations

import pytest

from app.notifier import _clean_addr, _clean_secret, _clean_text, _fmt


# ---------------------------------------------------------------------------
# _fmt – hinnan muotoilu
# ---------------------------------------------------------------------------

class TestFmt:
    def test_none_returns_dash(self):
        assert _fmt(None) == "-"

    def test_integer_price(self):
        assert _fmt(10.0) == "10,00 €"

    def test_decimal_price(self):
        assert _fmt(29.9) == "29,90 €"

    def test_large_price(self):
        assert _fmt(1299.0) == "1299,00 €"

    def test_zero(self):
        assert _fmt(0.0) == "0,00 €"


# ---------------------------------------------------------------------------
# _clean_text – erikoisvälilyöntien siivous
# ---------------------------------------------------------------------------

class TestCleanText:
    def test_nbsp_replaced(self):
        result = _clean_text("hinta\xa029,90")
        assert "\xa0" not in result
        assert "hinta 29,90" == result

    def test_narrow_nbsp_replaced(self):
        result = _clean_text("hinta 29,90")
        assert " " not in result

    def test_zero_width_removed(self):
        result = _clean_text("sala​inen")
        assert "​" not in result
        assert result == "salainen"

    def test_bom_removed(self):
        result = _clean_text("﻿alkaa")
        assert "﻿" not in result
        assert result == "alkaa"

    def test_normal_text_unchanged(self):
        text = "Hinta laski: Tuote — 29,90 €"
        assert _clean_text(text) == text

    def test_strips_whitespace(self):
        assert _clean_text("  teksti  ") == "teksti"

    def test_none_coerced(self):
        # Ei kaadu None-syötteellä (str(None) = "None")
        result = _clean_text(None)  # type: ignore[arg-type]
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _clean_addr – sähköpostiosoitteen siivous
# ---------------------------------------------------------------------------

class TestCleanAddr:
    def test_removes_spaces(self):
        assert _clean_addr("user @example.com") == "user@example.com"

    def test_removes_nbsp(self):
        assert _clean_addr("user\xa0@example.com") == "user@example.com"

    def test_removes_zero_width(self):
        assert _clean_addr("user​@example.com") == "user@example.com"

    def test_removes_bom(self):
        assert _clean_addr("﻿user@example.com") == "user@example.com"

    def test_clean_address_unchanged(self):
        assert _clean_addr("user@example.com") == "user@example.com"

    def test_empty_string(self):
        assert _clean_addr("") == ""


# ---------------------------------------------------------------------------
# _clean_secret – SMTP-tunnuksen/salasanan siivous
# ---------------------------------------------------------------------------

class TestCleanSecret:
    def test_removes_narrow_nbsp(self):
        # Gmail-sovellussalasana: "abcd efgh" → "abcdefgh" (narrow no-break space)
        assert _clean_secret("abcd efgh") == "abcdefgh"

    def test_keeps_ascii_space(self):
        # Tavallinen välilyönti sallitaan (salasana voi sisältää sen)
        assert _clean_secret("pass word") == "pass word"

    def test_removes_zero_width(self):
        assert _clean_secret("abc​def") == "abcdef"

    def test_removes_bom(self):
        assert _clean_secret("﻿password") == "password"

    def test_removes_zwj(self):
        assert _clean_secret("abc‍def") == "abcdef"

    def test_clean_secret_unchanged(self):
        assert _clean_secret("simplepassword") == "simplepassword"

    def test_strips_whitespace(self):
        assert _clean_secret("  secret  ") == "secret"
