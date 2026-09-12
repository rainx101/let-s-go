"""Anchor geocoding via OpenStreetMap (Nominatim). Turns a destination's
city/country into coordinates so the Phase 3 hotel/restaurant search can rank by
distance-to-anchor. Pure query building + an injectable network seam, so tests
never hit the network; fail-soft (PRD §11) — an unreachable/garbled source yields
no coordinates, never a crash. The rest of the app depends only on this module.

Nominatim usage policy: max ~1 request/second and a descriptive User-Agent."""

import json
import time
import urllib.parse
import urllib.request
from collections.abc import Callable

from lets_go.log import get_logger

logger = get_logger(__name__)

_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "lets-go-travel-planner/1.0"
_MIN_INTERVAL_S = 1.0  # Nominatim: at most ~1 request/second.

_last_call = 0.0


def place_query(*parts: str) -> str:
    """Free-text geocoding query from ordered parts, blanks dropped, e.g.
    place_query('Disneyland', 'Anaheim', 'USA') -> 'Disneyland, Anaheim, USA'."""
    return ", ".join(p.strip() for p in parts if p and p.strip())


def build_query(city: str, country: str) -> str:
    """Free-text query for a destination anchor, e.g. 'Anaheim, USA'.
    Blank parts are dropped so 'Tokyo' and 'Tokyo, Japan' both work."""
    return place_query(city, country)


def _throttle() -> None:
    """Space real requests at least ~1s apart (Nominatim policy)."""
    global _last_call
    wait = _MIN_INTERVAL_S - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def _fetch_json(url: str) -> list[dict]:
    """GET a Nominatim URL and parse JSON. Real network; injected in tests.
    Sends the required User-Agent and honors the ~1 req/sec rate limit."""
    _throttle()
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310 (fixed https URL)
        return json.load(resp)


def geocode(
    query: str,
    fetch_json: Callable[[str], list[dict]] = _fetch_json,
) -> tuple[float, float] | None:
    """Coordinates (lat, lon) for a place, or None when there's no match.
    Raises on a malformed result (KeyError/ValueError) — the caller decides
    whether to fall back (see `geocode_or_none`)."""
    if not query.strip():
        return None
    params = urllib.parse.urlencode({"q": query, "format": "json", "limit": 1})
    results = fetch_json(f"{_SEARCH_URL}?{params}")
    if not results:
        return None
    top = results[0]
    return (float(top["lat"]), float(top["lon"]))


def geocode_or_none(
    query: str,
    fetch_json: Callable[[str], list[dict]] = _fetch_json,
) -> tuple[float, float] | None:
    """Coordinates for a place, or None on no match *or* any failure — so the UI
    falls back to manual entry instead of crashing (PRD §11)."""
    try:
        return geocode(query, fetch_json=fetch_json)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        logger.warning("geocode failed for %r (%s); manual entry", query, exc)
        return None


# City comes from whichever address field the place happens to carry.
_CITY_FIELDS = ("city", "town", "village", "municipality", "county")


def parse_search(results: list[dict]) -> list[dict]:
    """Shape Nominatim search results into pick-list candidates — each a dict of
    display_name, lat, lon, city, country. Entries without coordinates are dropped."""
    places = []
    for r in results:
        if "lat" not in r or "lon" not in r:
            continue
        addr = r.get("address", {})
        display = r.get("display_name", "")
        city = next((addr[f] for f in _CITY_FIELDS if addr.get(f)), display.split(",")[0].strip())
        places.append(
            {
                "display_name": display,
                "lat": float(r["lat"]),
                "lon": float(r["lon"]),
                "city": city,
                "country": addr.get("country", ""),
            }
        )
    return places


def search(
    query: str,
    limit: int = 5,
    fetch_json: Callable[[str], list[dict]] = _fetch_json,
) -> list[dict]:
    """Top place matches for a query (name/city/country + coords) to pick from.
    Raises on a broken response — see `search_or_empty` for the fail-soft form."""
    params = urllib.parse.urlencode(
        {"q": query, "format": "json", "addressdetails": 1, "limit": limit}
    )
    return parse_search(fetch_json(f"{_SEARCH_URL}?{params}"))


def search_or_empty(
    query: str,
    fetch_json: Callable[[str], list[dict]] = _fetch_json,
) -> list[dict]:
    """Place matches for a query, or [] on a blank query / any failure (PRD §11)."""
    if not query.strip():
        return []
    try:
        return search(query, fetch_json=fetch_json)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        logger.warning("place search failed for %r (%s)", query, exc)
        return []
