"""Tests for currency conversion (static + live rates)."""

from decimal import Decimal
from urllib.error import URLError

import pytest

from lets_go.currency import (
    RATES,
    convert,
    currency_for_country,
    fetch_live_rates,
    live_rates_or_static,
)


# open.er-api.com returns rates as "units of X per 1 USD"; we store USD per unit.
def _fake_payload() -> dict:
    return {
        "result": "success",
        "base_code": "USD",
        "rates": {
            "USD": 1,
            "EUR": 0.9,  # -> USD per EUR = 1/0.9 = 1.111111...
            "JPY": 150,  # -> 1/150 = 0.006667
            "GBP": 0.8,
            "AUD": 1.5,
            "CAD": 1.25,
            "TWD": 32,
            "KRW": 1300,
            "THB": 35,
            "XYZ": 999,  # extra currency we don't support — ignored
        },
    }


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


def test_fetch_live_rates_inverts_payload_to_usd_per_unit():
    rates = fetch_live_rates(fetch_json=lambda _url: _fake_payload())
    # 1 / 0.9 = 1.1111... USD per EUR
    assert rates["EUR"] == Decimal("1") / Decimal("0.9")
    assert rates["USD"] == Decimal("1")


def test_fetch_live_rates_covers_supported_currencies_only():
    rates = fetch_live_rates(fetch_json=lambda _url: _fake_payload())
    assert set(rates) == set(RATES)  # XYZ dropped; nothing missing


def test_fetch_live_rates_raises_on_error_result():
    with pytest.raises(ValueError):
        fetch_live_rates(fetch_json=lambda _url: {"result": "error"})


def test_fetch_live_rates_raises_when_supported_currency_missing():
    payload = _fake_payload()
    del payload["rates"]["JPY"]
    with pytest.raises(KeyError):
        fetch_live_rates(fetch_json=lambda _url: payload)


def test_live_rates_or_static_returns_live_when_available():
    rates = live_rates_or_static(fetch_json=lambda _url: _fake_payload())
    assert rates["EUR"] == Decimal("1") / Decimal("0.9")  # not the static 1.08


def test_live_rates_or_static_falls_back_on_network_error():
    def _boom(_url: str) -> dict:
        raise URLError("down")

    assert live_rates_or_static(fetch_json=_boom) is RATES


def test_convert_uses_injected_rates():
    live = {"USD": Decimal("1"), "EUR": Decimal("1.2")}
    # 120 USD / 1.2 = 100 EUR (differs from the static 1.08 table)
    assert convert(Decimal("120"), "USD", "EUR", rates=live) == Decimal("100.00")
