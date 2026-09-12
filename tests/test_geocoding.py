"""Tests for anchor geocoding (OpenStreetMap / Nominatim), HTTP mocked."""

from urllib.error import URLError

from lets_go.geocoding import build_query, geocode, geocode_or_none, place_query


# Nominatim's /search returns a JSON list; we use the first result's lat/lon.
def _fake_results() -> list[dict]:
    return [
        {
            "lat": "33.8121",
            "lon": "-117.9190",
            "display_name": "Disneyland Park, Anaheim, California, USA",
        }
    ]


def test_place_query_joins_ordered_parts():
    assert place_query("Disneyland", "Anaheim", "USA") == "Disneyland, Anaheim, USA"


def test_place_query_drops_blank_and_trims_parts():
    assert place_query("  Eiffel Tower ", "", "  Paris  ") == "Eiffel Tower, Paris"


def test_build_query_joins_city_and_country():
    assert build_query("Anaheim", "USA") == "Anaheim, USA"


def test_build_query_omits_blank_country():
    assert build_query("Tokyo", "") == "Tokyo"


def test_build_query_trims_and_omits_blank_city():
    assert build_query("  ", "Japan") == "Japan"


def test_geocode_parses_first_result_to_floats():
    coords = geocode("Anaheim, USA", fetch_json=lambda _url: _fake_results())
    assert coords == (33.8121, -117.9190)


def test_geocode_returns_none_on_empty_results():
    assert geocode("Nowhereville", fetch_json=lambda _url: []) is None


def test_geocode_returns_none_for_blank_query():
    # No query to send; don't hit the network at all.
    def _boom(_url: str) -> list[dict]:
        raise AssertionError("should not fetch for a blank query")

    assert geocode("   ", fetch_json=_boom) is None


def test_geocode_or_none_falls_back_on_network_error():
    def _boom(_url: str) -> list[dict]:
        raise URLError("down")

    assert geocode_or_none("Anaheim, USA", fetch_json=_boom) is None


def test_geocode_or_none_falls_back_on_malformed_result():
    # First result missing lat/lon -> KeyError inside geocode, swallowed to None.
    assert geocode_or_none("Anaheim", fetch_json=lambda _url: [{"display_name": "x"}]) is None


def test_geocode_or_none_returns_coords_when_available():
    assert geocode_or_none("Anaheim, USA", fetch_json=lambda _url: _fake_results()) == (
        33.8121,
        -117.9190,
    )
