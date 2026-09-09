"""Currency conversion. Pure functions with no Streamlit or DB, so it's
unit-testable. Live rates come from open.er-api.com (base USD, no API key);
`RATES` is the static fallback used when that source is unreachable (PRD §11).
The rest of the app depends only on `convert`."""

import json
import urllib.request
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal
from urllib.error import URLError

from lets_go.log import get_logger

logger = get_logger(__name__)

# Free, keyless, base-USD source. `rates[X]` = units of X per 1 USD.
_LIVE_URL = "https://open.er-api.com/v6/latest/USD"

# Static fallback: 1 unit of the currency in USD. Used when the live fetch fails.
RATES: dict[str, Decimal] = {
    "USD": Decimal("1"),
    "EUR": Decimal("1.08"),
    "JPY": Decimal("0.0067"),
    "GBP": Decimal("1.27"),
    "AUD": Decimal("0.66"),
    "CAD": Decimal("0.74"),
    "TWD": Decimal("0.031"),
    "KRW": Decimal("0.00075"),
    "THB": Decimal("0.028"),
    "CNY": Decimal("0.14"),
    "IDR": Decimal("0.000061"),
}


# Country → currency for the currencies we support. Best-effort mapping; unknown
# or blank countries fall back to the caller's default (usually home currency).
_COUNTRY_CURRENCY: dict[str, str] = {
    "usa": "USD",
    "us": "USD",
    "united states": "USD",
    "united states of america": "USD",
    "america": "USD",
    "japan": "JPY",
    "uk": "GBP",
    "united kingdom": "GBP",
    "britain": "GBP",
    "great britain": "GBP",
    "england": "GBP",
    "scotland": "GBP",
    "wales": "GBP",
    "australia": "AUD",
    "canada": "CAD",
    "taiwan": "TWD",
    "korea": "KRW",
    "south korea": "KRW",
    "thailand": "THB",
    "china": "CNY",
    "indonesia": "IDR",
    "france": "EUR",
    "germany": "EUR",
    "italy": "EUR",
    "spain": "EUR",
    "portugal": "EUR",
    "netherlands": "EUR",
    "ireland": "EUR",
    "greece": "EUR",
    "austria": "EUR",
    "belgium": "EUR",
    "finland": "EUR",
}


def currency_for_country(country: str, default: str) -> str:
    """Best-effort currency code for a country name; `default` if unknown/blank."""
    return _COUNTRY_CURRENCY.get(country.strip().casefold(), default)


def convert(
    amount: Decimal, from_ccy: str, to_ccy: str, rates: dict[str, Decimal] | None = None
) -> Decimal:
    """Convert an amount between known currencies (via USD), rounded to 2dp.
    `rates` is USD-per-unit; defaults to the static table. Raises KeyError for an
    unknown currency — they come from our fixed list."""
    if rates is None:
        rates = RATES
    if from_ccy == to_ccy:
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    usd = amount * rates[from_ccy]
    return (usd / rates[to_ccy]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _fetch_json(url: str) -> dict:
    """GET a URL and parse JSON. Real network; injected in tests."""
    with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310 (fixed https URL)
        return json.load(resp)


def fetch_live_rates(
    fetch_json: Callable[[str], dict] = _fetch_json,
) -> dict[str, Decimal]:
    """Live USD-per-unit rates for the currencies we support.

    The source gives units-of-X-per-USD, so we invert. Raises on a bad response
    (ValueError) or a missing supported currency (KeyError) — the caller decides
    whether to fall back."""
    payload = fetch_json(_LIVE_URL)
    if payload.get("result") != "success":
        raise ValueError(f"rate source returned {payload.get('result')!r}")
    per_usd = payload["rates"]
    return {ccy: Decimal("1") / Decimal(str(per_usd[ccy])) for ccy in RATES}


def live_rates_or_static(
    fetch_json: Callable[[str], dict] = _fetch_json,
) -> dict[str, Decimal]:
    """Live rates when reachable, else the static `RATES` table (PRD §11)."""
    try:
        return fetch_live_rates(fetch_json=fetch_json)
    except (URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
        logger.warning("live rate fetch failed (%s); using static rates", exc)
        return RATES
