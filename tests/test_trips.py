"""Tests for the pure trip helpers (no DB)."""

from datetime import date

from lets_go.trips import DraftLeg, trip_date_range, validate_new_item, validate_new_trip


def test_date_range_spans_earliest_start_to_latest_end():
    legs = [
        DraftLeg(city="Tokyo", start_date=date(2026, 5, 1), end_date=date(2026, 5, 4)),
        DraftLeg(city="Osaka", start_date=date(2026, 5, 4), end_date=date(2026, 5, 7)),
    ]
    assert trip_date_range(legs) == (date(2026, 5, 1), date(2026, 5, 7))


def test_date_range_ignores_missing_dates():
    legs = [DraftLeg(city="Lisbon"), DraftLeg(city="Porto", start_date=date(2026, 6, 1))]
    assert trip_date_range(legs) == (date(2026, 6, 1), None)


def test_date_range_empty():
    assert trip_date_range([]) == (None, None)


def _leg(
    city: str = "Tokyo",
    start_date: date = date(2026, 5, 1),
    end_date: date = date(2026, 5, 2),
    need_flight: bool = False,
    from_city: str = "",
) -> DraftLeg:
    """A valid draft leg (Tokyo, one-night range) with fields overridable."""
    return DraftLeg(
        city=city,
        start_date=start_date,
        end_date=end_date,
        need_flight=need_flight,
        from_city=from_city,
    )


def test_validate_ok():
    assert validate_new_trip("Japan trip", [_leg()]) == []


def test_validate_requires_dates():
    errors = validate_new_trip("Japan", [DraftLeg(city="Tokyo")])
    assert any("pick start and end dates" in e for e in errors)


def test_validate_rejects_same_day_range():
    errors = validate_new_trip("Japan", [_leg(end_date=date(2026, 5, 1))])
    assert any("end date must be after" in e for e in errors)


def test_validate_flight_requires_departure_city():
    errors = validate_new_trip("Japan", [_leg(need_flight=True)])
    assert any("departure city" in e for e in errors)


def test_validate_ok_with_departure_city_for_flight():
    legs = [_leg(need_flight=True, from_city="Los Angeles")]
    assert validate_new_trip("Japan", legs) == []


def test_validate_requires_name():
    assert "Trip needs a name." in validate_new_trip("   ", [DraftLeg(city="Tokyo")])


def test_validate_requires_a_leg():
    assert "Add at least one city." in validate_new_trip("Japan", [])


def test_validate_requires_city_name():
    errors = validate_new_trip("Japan", [DraftLeg(city="  ")])
    assert any("City 1 needs a name." in e for e in errors)


def test_validate_flags_end_before_start():
    legs = [DraftLeg(city="Tokyo", start_date=date(2026, 5, 5), end_date=date(2026, 5, 1))]
    errors = validate_new_trip("Japan", legs)
    assert any("end date must be after" in e for e in errors)


def test_validate_item_ok():
    assert validate_new_item("Sushi dinner", 40.0) == []


def test_validate_item_requires_name():
    assert "Item needs a name." in validate_new_item("  ", 40.0)


def test_validate_item_rejects_negative_cost():
    errors = validate_new_item("Flight", -10.0)
    assert any("cost can't be negative" in e for e in errors)
