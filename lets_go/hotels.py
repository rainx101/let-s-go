"""Hotel search via Xotelo (free, keyless; TripAdvisor-backed). One thin client;
the rest of the app depends on our `Hotel` shape, not the vendor JSON. Network is
an injectable seam so tests never hit it; fail-soft (PRD §11) — an unreachable or
garbled source yields no hotels, never a crash. Options are ranked by
distance-to-anchor × price within the flight+hotel budget (PRD §6/§7).

Xotelo needs no API key. `/list` returns hotels (coords + price range) for a
TripAdvisor location key; `/rates` returns per-OTA nightly prices for a hotel +
dates. Prices are USD."""

import json
import math
import re
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from lets_go.distance import Coord, haversine
from lets_go.log import get_logger

logger = get_logger(__name__)

_API = "https://data.xotelo.com/api"
_USER_AGENT = "lets-go-travel-planner/1.0"
_MIN_INTERVAL_S = 0.3  # courtesy throttle (Xotelo documents no hard limit)
_LOCATION_KEY_RE = re.compile(r"g\d+")

_last_call = 0.0


@dataclass(frozen=True)
class Hotel:
    """One hotel option in our own shape (independent of the vendor response)."""

    key: str
    name: str
    lat: float
    lon: float
    price_min: Decimal | None
    price_max: Decimal | None
    rating: float | None
    url: str


def parse_location_key(text: str) -> str | None:
    """The TripAdvisor location id (e.g. 'g293916') from a pasted Hotels URL or a
    bare key; None when there's no gNNN token to find."""
    match = _LOCATION_KEY_RE.search(text or "")
    return match.group(0) if match else None


def _throttle() -> None:
    """Space real requests at least ~1s apart (courtesy for a free service)."""
    global _last_call
    wait = _MIN_INTERVAL_S - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def _fetch_json(url: str) -> dict:
    """GET a Xotelo URL and parse JSON. Real network; injected in tests."""
    _throttle()
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310 (fixed https URL)
        return json.load(resp)


def _price(value: object) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _require_ok(payload: dict) -> dict:
    """Return the payload's `result`, raising ValueError on an API error."""
    if payload.get("error"):
        raise ValueError(payload["error"].get("message", "xotelo error"))
    return payload["result"]


def parse_hotels(payload: dict) -> list[Hotel]:
    """Shape a Xotelo /list response into Hotels; entries without coordinates are
    dropped (they can't be distance-ranked). Raises on an API error / bad shape."""
    hotels = []
    for h in _require_ok(payload)["list"]:
        geo = h.get("geo") or {}
        if geo.get("latitude") is None or geo.get("longitude") is None:
            continue
        prices = h.get("price_ranges") or {}
        review = h.get("review_summary") or {}
        hotels.append(
            Hotel(
                key=h["key"],
                name=h["name"],
                lat=float(geo["latitude"]),
                lon=float(geo["longitude"]),
                price_min=_price(prices.get("minimum")),
                price_max=_price(prices.get("maximum")),
                rating=review.get("rating"),
                url=h.get("url", ""),
            )
        )
    return hotels


def list_hotels(
    location_key: str,
    limit: int = 30,
    fetch_json: Callable[[str], dict] = _fetch_json,
) -> list[Hotel]:
    """Hotels for a TripAdvisor location key (coords + price range each). Raises on
    a broken response — see `list_hotels_or_empty` for the fail-soft form."""
    params = urllib.parse.urlencode({"location_key": location_key, "limit": limit})
    return parse_hotels(fetch_json(f"{_API}/list?{params}"))


def list_hotels_or_empty(
    location_key: str,
    fetch_json: Callable[[str], dict] = _fetch_json,
) -> list[Hotel]:
    """Hotels for a location key, or [] on a blank key / any failure (PRD §11)."""
    if not location_key:
        return []
    try:
        return list_hotels(location_key, fetch_json=fetch_json)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        logger.warning("hotel list failed for %r (%s)", location_key, exc)
        return []


def rate_range(
    hotel_key: str,
    chk_in: date,
    chk_out: date,
    fetch_json: Callable[[str], dict] = _fetch_json,
) -> tuple[Decimal, Decimal] | None:
    """(cheapest, priciest) nightly rate (USD) across OTAs for the exact stay, or
    None when no rate is offered. Date-specific, unlike the /list price range.
    Raises on a broken response — see `rate_range_or_none`."""
    params = urllib.parse.urlencode(
        {"hotel_key": hotel_key, "chk_in": chk_in.isoformat(), "chk_out": chk_out.isoformat()}
    )
    rates = [r["rate"] for r in _require_ok(fetch_json(f"{_API}/rates?{params}"))["rates"]]
    valid = [r for r in rates if r is not None]
    if not valid:
        return None
    lo, hi = _price(min(valid)), _price(max(valid))
    assert lo is not None and hi is not None  # valid is non-empty
    return (lo, hi)


def rate_range_or_none(
    hotel_key: str,
    chk_in: date,
    chk_out: date,
    fetch_json: Callable[[str], dict] = _fetch_json,
) -> tuple[Decimal, Decimal] | None:
    """Date-specific price range, or None on any failure (PRD §11)."""
    try:
        return rate_range(hotel_key, chk_in, chk_out, fetch_json=fetch_json)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        logger.warning("hotel rate failed for %r (%s)", hotel_key, exc)
        return None


def cheapest_rate(
    hotel_key: str,
    chk_in: date,
    chk_out: date,
    fetch_json: Callable[[str], dict] = _fetch_json,
) -> Decimal | None:
    """Cheapest nightly rate (USD) across OTAs for a hotel + stay, or None when no
    rate is offered. Raises on a broken response — see `cheapest_rate_or_none`."""
    rng = rate_range(hotel_key, chk_in, chk_out, fetch_json=fetch_json)
    return rng[0] if rng is not None else None


def cheapest_rate_or_none(
    hotel_key: str,
    chk_in: date,
    chk_out: date,
    fetch_json: Callable[[str], dict] = _fetch_json,
) -> Decimal | None:
    """Cheapest nightly rate, or None on any failure (PRD §11)."""
    try:
        return cheapest_rate(hotel_key, chk_in, chk_out, fetch_json=fetch_json)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        logger.warning("hotel rate failed for %r (%s)", hotel_key, exc)
        return None


def rank_hotels(
    hotels: list[Hotel],
    anchor: Coord | None,
    price_cap: Decimal | None,
) -> tuple[list[Hotel], list[Hotel]]:
    """Split hotels into (within-budget, over-budget) and order each by
    distance-to-anchor × price — nearest *and* cheapest first (PRD §6/§7). Price
    breaks ties (so equally-near hotels still order cheapest-first, and a hotel
    right at the anchor doesn't collapse to a zero score). With no anchor, order by
    price alone. `price_cap` and prices are the same currency (USD). Unknown-price
    hotels sort last and stay in the within-budget list (they can't be ruled out)."""

    def sort_key(h: Hotel) -> tuple[float, float]:
        price = float(h.price_min) if h.price_min is not None else math.inf
        if anchor is None:
            return (price, price)
        dist = haversine(anchor, (h.lat, h.lon))
        combo = math.inf if math.isinf(price) else dist * price
        return (combo, price)

    within, over = [], []
    for h in hotels:
        if price_cap is not None and h.price_min is not None and h.price_min > price_cap:
            over.append(h)
        else:
            within.append(h)
    within.sort(key=sort_key)
    over.sort(key=sort_key)
    return within, over
