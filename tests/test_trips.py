"""Tests for the pure trip helpers (no DB)."""

from datetime import date

from lets_go.trips import DraftLeg, trip_date_range, validate_new_trip


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


def test_validate_ok():
    legs = [DraftLeg(city="Tokyo")]
    assert validate_new_trip("Japan trip", legs) == []


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
    assert any("end date is before start date" in e for e in errors)
