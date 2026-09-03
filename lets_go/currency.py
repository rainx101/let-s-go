"""Currency conversion. Pure functions with a static placeholder rate table —
no Streamlit or DB, so it's unit-testable. A live rate source replaces RATES in
Phase 2 (PRD §10); the rest of the app depends only on `convert`."""

from decimal import ROUND_HALF_UP, Decimal

# Placeholder rates: 1 unit of the currency in USD. Phase 2 wires a live source.
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


def convert(amount: Decimal, from_ccy: str, to_ccy: str) -> Decimal:
    """Convert an amount between known currencies (via USD), rounded to 2dp.
    Raises KeyError for an unknown currency — they come from our fixed list."""
    if from_ccy == to_ccy:
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    usd = amount * RATES[from_ccy]
    return (usd / RATES[to_ccy]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
