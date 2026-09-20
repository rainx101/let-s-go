"""Tests for the Xotelo hotel client + anchor ranking (pure; network is mocked)."""

from datetime import date
from decimal import Decimal

import pytest

from lets_go.hotels import (
    Hotel,
    cheapest_rate,
    cheapest_rate_or_none,
    list_hotels,
    list_hotels_or_empty,
    parse_location_key,
    rank_hotels,
    rate_range,
    rate_range_or_none,
)

ANCHOR = (33.812, -117.919)  # Disneyland-ish


def _hotel(key: str, lat: float, lon: float, price_min) -> Hotel:
    return Hotel(
        key=key,
        name=key,
        lat=lat,
        lon=lon,
        price_min=Decimal(str(price_min)) if price_min is not None else None,
        price_max=None,
        rating=None,
        url="",
    )


def test_parse_location_key_from_tripadvisor_url():
    url = "https://www.tripadvisor.com/Hotels-g293916-Bangkok-Hotels.html"
    assert parse_location_key(url) == "g293916"


def test_parse_location_key_from_bare_key():
    assert parse_location_key("g29092") == "g29092"


def test_parse_location_key_none_on_junk():
    assert parse_location_key("just some text") is None
    assert parse_location_key("") is None


def test_list_hotels_maps_fields(xotelo_list_payload):
    hotels = list_hotels("g29092", fetch_json=lambda _url: xotelo_list_payload)
    assert [h.name for h in hotels] == ["SpringHill Suites", "Fairfield Inn"]
    first = hotels[0]
    assert first.key == "g29092-d17738446"
    assert (first.lat, first.lon) == (33.804783, -117.90591)
    assert first.price_min == Decimal("182")
    assert first.rating == 4.2


def test_list_hotels_drops_coordless(xotelo_list_payload):
    hotels = list_hotels("g29092", fetch_json=lambda _url: xotelo_list_payload)
    assert all(h.name != "No Coordinates Inn" for h in hotels)


def test_list_hotels_raises_on_api_error():
    payload = {"error": {"status_code": 401, "message": "nope"}, "result": None}
    with pytest.raises(ValueError, match="nope"):
        list_hotels("g29092", fetch_json=lambda _url: payload)


def test_list_hotels_or_empty_swallows_failure():
    def boom(_url):
        raise OSError("network down")

    assert list_hotels_or_empty("g29092", fetch_json=boom) == []


def test_list_hotels_or_empty_blank_key():
    assert list_hotels_or_empty("", fetch_json=lambda _url: {}) == []


def test_cheapest_rate_returns_minimum(xotelo_rates_payload):
    rate = cheapest_rate(
        "g29092-d113856",
        date(2026, 11, 1),
        date(2026, 11, 3),
        fetch_json=lambda _url: xotelo_rates_payload,
    )
    assert rate == Decimal("219")


def test_rate_range_returns_min_and_max(xotelo_rates_payload):
    rng = rate_range(
        "g29092-d113856",
        date(2026, 11, 1),
        date(2026, 11, 3),
        fetch_json=lambda _url: xotelo_rates_payload,
    )
    assert rng == (Decimal("219"), Decimal("246"))


def test_rate_range_none_when_no_rates():
    payload = {"error": None, "result": {"rates": []}}
    rng = rate_range("k", date(2026, 11, 1), date(2026, 11, 3), fetch_json=lambda _url: payload)
    assert rng is None


def test_rate_range_or_none_swallows_failure():
    def boom(_url):
        raise OSError("network down")

    assert rate_range_or_none("k", date(2026, 11, 1), date(2026, 11, 3), fetch_json=boom) is None


def test_cheapest_rate_or_none_swallows_failure():
    def boom(_url):
        raise OSError("network down")

    assert cheapest_rate_or_none("k", date(2026, 11, 1), date(2026, 11, 3), fetch_json=boom) is None


def test_rank_hotels_nearest_and_cheapest_first():
    near_cheap = _hotel("near_cheap", 33.812, -117.919, 150)
    near_dear = _hotel("near_dear", 33.812, -117.919, 400)
    far_cheap = _hotel("far_cheap", 33.90, -117.60, 150)
    within, over = rank_hotels([far_cheap, near_dear, near_cheap], ANCHOR, price_cap=None)
    assert [h.key for h in within] == ["near_cheap", "near_dear", "far_cheap"]
    assert over == []


def test_rank_hotels_splits_over_budget():
    cheap = _hotel("cheap", 33.812, -117.919, 150)
    dear = _hotel("dear", 33.812, -117.919, 400)
    within, over = rank_hotels([dear, cheap], ANCHOR, price_cap=Decimal("200"))
    assert [h.key for h in within] == ["cheap"]
    assert [h.key for h in over] == ["dear"]


def test_rank_hotels_no_anchor_sorts_by_price():
    a = _hotel("a", 0.0, 0.0, 300)
    b = _hotel("b", 0.0, 0.0, 120)
    within, _over = rank_hotels([a, b], anchor=None, price_cap=None)
    assert [h.key for h in within] == ["b", "a"]


def test_rank_hotels_unknown_price_sorts_last_and_stays_within():
    known = _hotel("known", 33.812, -117.919, 150)
    unknown = _hotel("unknown", 33.812, -117.919, None)
    within, over = rank_hotels([unknown, known], ANCHOR, price_cap=Decimal("200"))
    assert [h.key for h in within] == ["known", "unknown"]
    assert over == []
