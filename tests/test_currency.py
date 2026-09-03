"""Tests for currency conversion (static placeholder rates)."""

from decimal import Decimal

from lets_go.currency import convert, currency_for_country


def test_convert_same_currency_quantizes():
    assert convert(Decimal("40"), "USD", "USD") == Decimal("40.00")


def test_convert_foreign_to_home():
    # 6000 JPY * 0.0067 = 40.20 USD
    assert convert(Decimal("6000"), "JPY", "USD") == Decimal("40.20")


def test_convert_home_to_foreign():
    # 108 USD / 1.08 = 100.00 EUR
    assert convert(Decimal("108"), "USD", "EUR") == Decimal("100.00")


def test_convert_rounds_to_two_places():
    # 1 JPY -> 0.0067 USD, rounds to 0.01
    assert convert(Decimal("1"), "JPY", "USD") == Decimal("0.01")


def test_currency_for_country_known():
    assert currency_for_country("Japan", "USD") == "JPY"


def test_currency_for_country_alias_and_case_insensitive():
    assert currency_for_country("  united kingdom ", "USD") == "GBP"


def test_currency_for_country_unknown_falls_back_to_default():
    assert currency_for_country("Narnia", "USD") == "USD"


def test_currency_for_country_empty_falls_back():
    assert currency_for_country("", "EUR") == "EUR"
