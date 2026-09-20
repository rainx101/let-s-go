"""Shared pytest fixtures (DRY setup for tests)."""

import pytest


@pytest.fixture
def sample_costs() -> list[float]:
    """A small set of item costs in the home currency."""
    return [500.0, 300.0, 120.0]


@pytest.fixture
def xotelo_list_payload() -> dict:
    """A trimmed Xotelo /list response: two hotels with coordinates + price ranges
    and one without coordinates (which the client must drop)."""
    return {
        "error": None,
        "result": {
            "total_count": 3,
            "limit": 30,
            "offset": 0,
            "list": [
                {
                    "name": "SpringHill Suites",
                    "key": "g29092-d17738446",
                    "price_ranges": {"minimum": 182, "maximum": 468},
                    "review_summary": {"rating": 4.2, "count": 570},
                    "geo": {"latitude": 33.804783, "longitude": -117.90591},
                    "url": "https://www.tripadvisor.com/Hotel_Review-g29092-d17738446.html",
                },
                {
                    "name": "Fairfield Inn",
                    "key": "g29092-d113856",
                    "price_ranges": {"minimum": 258, "maximum": 480},
                    "review_summary": {"rating": 4.0, "count": 678},
                    "geo": {"latitude": 33.811428, "longitude": -117.91536},
                    "url": "https://www.tripadvisor.com/Hotel_Review-g29092-d113856.html",
                },
                {
                    "name": "No Coordinates Inn",
                    "key": "g29092-d999999",
                    "price_ranges": {"minimum": 90, "maximum": 120},
                    "review_summary": {"rating": 3.5, "count": 12},
                    "geo": {"latitude": None, "longitude": None},
                    "url": "https://www.tripadvisor.com/Hotel_Review-g29092-d999999.html",
                },
            ],
        },
        "timestamp": 1789874108266,
    }


@pytest.fixture
def xotelo_rates_payload() -> dict:
    """A trimmed Xotelo /rates response: per-OTA nightly rates for one hotel."""
    return {
        "error": None,
        "result": {
            "chk_in": "2026-11-01",
            "chk_out": "2026-11-03",
            "currency": "USD",
            "rates": [
                {"code": "Marriott1", "name": "Fairfield Inn", "rate": 229, "tax": None},
                {"code": "BookingCom", "name": "Booking.com", "rate": 246, "tax": None},
                {"code": "Agoda", "name": "Agoda.com", "rate": 219, "tax": None},
            ],
        },
        "timestamp": 1789874124818,
    }
