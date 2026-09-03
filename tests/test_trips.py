"""Tests for the pure trip helpers (no DB)."""

import json
from datetime import date
from decimal import Decimal

from lets_go.trips import (
    DraftLeg,
    dates_overlap,
    destination_budgets,
    export_json,
    normalize_place,
    trip_date_range,
    validate_budget_caps,
    validate_new_item,
    validate_new_trip,
)


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
    budget_cap: Decimal | None = None,
) -> DraftLeg:
    """A valid draft leg (Tokyo, one-night range) with fields overridable."""
    return DraftLeg(
        city=city,
        start_date=start_date,
        end_date=end_date,
        need_flight=need_flight,
        from_city=from_city,
        budget_cap=budget_cap,
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


def test_validate_flags_same_from_and_destination():
    errors = validate_new_trip("Japan", [_leg(city="Tokyo", from_city=" tokyo ")])
    assert any("same as the departure city" in e for e in errors)


def test_normalize_place_trims_collapses_and_titlecases():
    assert normalize_place("  new   york ") == "New York"


def test_normalize_place_empty_stays_empty():
    assert normalize_place("   ") == ""


def test_destination_budgets_even_split_when_no_caps():
    legs = [_leg(city="Tokyo"), _leg(city="Osaka")]
    assert destination_budgets(Decimal("500"), legs) == [Decimal("250"), Decimal("250")]


def test_destination_budgets_single_stop_gets_whole_budget():
    assert destination_budgets(Decimal("500"), [_leg()]) == [Decimal("500")]


def test_destination_budgets_explicit_cap_then_split_remainder():
    legs = [_leg(city="Tokyo", budget_cap=Decimal("300")), _leg(city="Osaka")]
    assert destination_budgets(Decimal("500"), legs) == [Decimal("300"), Decimal("200")]


def test_destination_budgets_no_overall_cap_returns_leg_caps():
    legs = [_leg(city="Tokyo", budget_cap=Decimal("100")), _leg(city="Osaka")]
    assert destination_budgets(None, legs) == [Decimal("100"), None]


def test_dates_overlap_true_for_intersecting_ranges():
    a = _leg(city="A", start_date=date(2026, 5, 1), end_date=date(2026, 5, 5))
    b = _leg(city="B", start_date=date(2026, 5, 4), end_date=date(2026, 5, 7))
    assert dates_overlap(a, b) is True


def test_dates_overlap_false_when_sharing_only_a_boundary_day():
    a = _leg(city="A", start_date=date(2026, 5, 1), end_date=date(2026, 5, 4))
    b = _leg(city="B", start_date=date(2026, 5, 4), end_date=date(2026, 5, 7))
    assert dates_overlap(a, b) is False


def test_dates_overlap_false_for_disjoint_ranges():
    a = _leg(city="A", start_date=date(2026, 5, 1), end_date=date(2026, 5, 3))
    b = _leg(city="B", start_date=date(2026, 5, 5), end_date=date(2026, 5, 7))
    assert dates_overlap(a, b) is False


def test_validate_flags_overlapping_destinations():
    legs = [
        _leg(city="Tokyo", start_date=date(2026, 5, 1), end_date=date(2026, 5, 5)),
        _leg(city="Osaka", start_date=date(2026, 5, 4), end_date=date(2026, 5, 7)),
    ]
    errors = validate_new_trip("Japan", legs)
    assert any("overlap" in e for e in errors)


def test_export_json_nests_items_and_serializes_types():
    trips = [
        {
            "id": 1,
            "name": "Japan",
            "budget_cap": Decimal("2000"),
            "created_at": date(2026, 9, 1),
            "legs": [],
        }
    ]
    items_by_trip = {1: [{"id": 10, "name": "Ramen", "cost": Decimal("40.20")}]}
    out = json.loads(export_json(trips, items_by_trip))
    assert out["version"] == 1
    assert out["trips"][0]["budget_cap"] == "2000"  # Decimal → string
    assert out["trips"][0]["created_at"] == "2026-09-01"  # date → isoformat
    assert out["trips"][0]["items"][0]["cost"] == "40.20"


def test_export_json_empty_when_no_trips():
    assert json.loads(export_json([], {})) == {"version": 1, "trips": []}


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


def test_budget_caps_ok_when_sum_within_trip_cap():
    legs = [_leg(budget_cap=Decimal("400")), _leg(city="Osaka", budget_cap=Decimal("500"))]
    assert validate_budget_caps(Decimal("1000"), legs) == []


def test_budget_caps_flagged_when_sum_exceeds_trip_cap():
    legs = [_leg(budget_cap=Decimal("700")), _leg(city="Osaka", budget_cap=Decimal("500"))]
    errors = validate_budget_caps(Decimal("1000"), legs)
    assert any("exceed the trip cap" in e for e in errors)


def test_budget_caps_ignores_stops_without_a_cap():
    legs = [_leg(budget_cap=Decimal("900")), _leg(city="Osaka")]
    assert validate_budget_caps(Decimal("1000"), legs) == []


def test_budget_caps_no_constraint_without_trip_cap():
    legs = [_leg(budget_cap=Decimal("900")), _leg(city="Osaka", budget_cap=Decimal("900"))]
    assert validate_budget_caps(None, legs) == []
