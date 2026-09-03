"""Trips data layer: pure helpers (validation, date range) + DB access.
Pure helpers have no Streamlit/DB deps so they're unit-testable."""

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from psycopg.rows import dict_row

from lets_go.db import get_connection


@dataclass
class DraftLeg:
    """A city/leg being drafted in the UI before the trip is saved.
    `from_city`/`from_country` are the flight origin (for flight search)."""

    city: str
    country: str = ""
    from_city: str = ""
    from_country: str = ""
    start_date: date | None = None
    end_date: date | None = None
    need_flight: bool = False
    need_hotel: bool = False
    round_trip: bool = False
    budget_cap: Decimal | None = None


# --- pure helpers (testable) ------------------------------------------------


def normalize_place(name: str) -> str:
    """Tidy a place name: trim, collapse inner whitespace, Title Case.
    Cheap cleanup so obvious formatting differences don't trip up planning;
    real place validation (geocoding) comes in Phase 2."""
    return " ".join(name.split()).title()


def leg_endpoint(leg: DraftLeg) -> tuple[str, str]:
    """Where you are after this leg — the origin if it's a round trip (you return
    to the start), otherwise the destination. Used to autofill the next leg's From."""
    if leg.round_trip:
        return leg.from_city, leg.from_country
    return leg.city, leg.country


def trip_date_range(legs: list[DraftLeg]) -> tuple[date | None, date | None]:
    """Earliest start and latest end across all legs (ignoring blanks)."""
    starts = [leg.start_date for leg in legs if leg.start_date]
    ends = [leg.end_date for leg in legs if leg.end_date]
    return (min(starts) if starts else None, max(ends) if ends else None)


def dates_overlap(a: DraftLeg, b: DraftLeg) -> bool:
    """True if two legs' date ranges genuinely overlap. Sharing a single
    boundary day (one ends the day the other starts) is allowed."""
    if not (a.start_date and a.end_date and b.start_date and b.end_date):
        return False
    return a.start_date < b.end_date and b.start_date < a.end_date


def validate_new_trip(name: str, legs: list[DraftLeg]) -> list[str]:
    """Return a list of problems with the draft trip. Empty list means valid."""
    errors: list[str] = []
    if not name.strip():
        errors.append("Trip needs a name.")
    if not legs:
        errors.append("Add at least one city.")
    for i, leg in enumerate(legs, start=1):
        if not leg.city.strip():
            errors.append(f"City {i} needs a name.")
        if not leg.start_date or not leg.end_date:
            errors.append(f"City {i}: pick start and end dates.")
        elif leg.end_date <= leg.start_date:
            errors.append(f"City {i}: end date must be after the start date.")
        if leg.need_flight and not leg.from_city.strip():
            errors.append(f"City {i}: add a departure city to search flights.")
        if leg.round_trip and not leg.from_city.strip():
            errors.append(f"City {i}: a round trip needs a departure city to return to.")
        origin = leg.from_city.strip()
        if origin and origin.casefold() == leg.city.strip().casefold():
            errors.append(f"City {i}: destination can't be the same as the departure city.")
    for a_i in range(len(legs)):
        for b_i in range(a_i + 1, len(legs)):
            if dates_overlap(legs[a_i], legs[b_i]):
                na = legs[a_i].city.strip() or f"City {a_i + 1}"
                nb = legs[b_i].city.strip() or f"City {b_i + 1}"
                errors.append(f"Dates for {na} and {nb} overlap.")
    return errors


def destination_budgets(overall_cap: Decimal | None, legs: list[DraftLeg]) -> list[Decimal | None]:
    """Per-destination budget (home currency): a stop's own cap when set,
    otherwise an even share of the overall budget left after the capped stops.
    With no overall cap, only the explicit per-stop caps are returned."""
    caps = [leg.budget_cap for leg in legs]
    if overall_cap is None:
        return caps
    capped_total = sum((c for c in caps if c is not None), Decimal(0))
    capless = [c for c in caps if c is None]
    remaining = max(overall_cap - capped_total, Decimal(0))
    share = remaining / len(capless) if capless else Decimal(0)
    return [c if c is not None else share for c in caps]


def validate_budget_caps(trip_cap: Decimal | None, legs: list[DraftLeg]) -> list[str]:
    """Per-destination caps may not sum past the overall trip cap.
    No trip cap means no constraint; stops without a cap don't count."""
    if trip_cap is None:
        return []
    total = sum((leg.budget_cap for leg in legs if leg.budget_cap is not None), Decimal(0))
    if total > trip_cap:
        return [f"Destination budgets ({total}) exceed the trip cap ({trip_cap})."]
    return []


def _json_safe(value: object) -> str:
    """JSON encoder fallback for the types our rows carry."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def export_json(trips: list[dict], items_by_trip: dict[int, list[dict]]) -> str:
    """Serialize trips (with their legs) and items to a JSON backup string."""
    payload = {
        "version": 1,
        "trips": [{**trip, "items": items_by_trip.get(trip["id"], [])} for trip in trips],
    }
    return json.dumps(payload, default=_json_safe, indent=2, ensure_ascii=False)


def validate_new_item(name: str, cost: float) -> list[str]:
    """Return a list of problems with a draft item. Empty list means valid."""
    errors: list[str] = []
    if not name.strip():
        errors.append("Item needs a name.")
    if cost < 0:
        errors.append("Item cost can't be negative.")
    return errors


# --- DB access --------------------------------------------------------------


def create_trip(
    name: str,
    home_currency: str,
    budget_cap: Decimal | None,
    legs: list[DraftLeg],
    trip_type: str = "round_trip",
) -> int:
    """Insert a trip and its legs atomically; return the new trip id."""
    conn = get_connection()
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            "INSERT INTO trips (name, home_currency, budget_cap, trip_type) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (name.strip(), home_currency, budget_cap, trip_type),
        )
        row = cur.fetchone()
        assert row is not None  # INSERT ... RETURNING always yields a row
        trip_id = row[0]
        for pos, leg in enumerate(legs):
            cur.execute(
                "INSERT INTO legs (trip_id, city, country, from_city, from_country, "
                "start_date, end_date, need_flight, need_hotel, round_trip, budget_cap, "
                "position) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    trip_id,
                    leg.city.strip(),
                    leg.country.strip() or None,
                    leg.from_city.strip() or None,
                    leg.from_country.strip() or None,
                    leg.start_date,
                    leg.end_date,
                    leg.need_flight,
                    leg.need_hotel,
                    leg.round_trip,
                    leg.budget_cap,
                    pos,
                ),
            )
    return trip_id


def list_trips() -> list[dict]:
    """All trips (newest first), each with a `legs` list attached."""
    conn = get_connection()
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, name, home_currency, budget_cap, trip_type, created_at "
            "FROM trips ORDER BY created_at DESC"
        )
        trips = cur.fetchall()
        cur.execute(
            "SELECT id, trip_id, city, country, from_city, from_country, start_date, end_date, "
            "need_flight, need_hotel, round_trip, budget_cap, position FROM legs "
            "ORDER BY position"
        )
        legs = cur.fetchall()

    by_trip: dict[int, list[dict]] = {}
    for leg in legs:
        by_trip.setdefault(leg["trip_id"], []).append(leg)
    for trip in trips:
        trip["legs"] = by_trip.get(trip["id"], [])
    return trips


def add_item(
    trip_id: int,
    leg_id: int | None,
    category: str,
    name: str,
    cost: Decimal,
    currency: str,
    day: int | None,
) -> int:
    """Insert one planned item (cost in its original `currency`); return its id."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO items (trip_id, leg_id, category, name, cost, currency, day) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (trip_id, leg_id, category, name.strip(), cost, currency, day),
        )
        row = cur.fetchone()
        assert row is not None  # INSERT ... RETURNING always yields a row
        return row[0]


def list_items(trip_id: int) -> list[dict]:
    """All items for a trip, ordered by leg, then day, then position."""
    conn = get_connection()
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT i.id, i.leg_id, i.category, i.name, i.cost, i.currency, i.day, i.position "
            "FROM items i LEFT JOIN legs l ON l.id = i.leg_id "
            "WHERE i.trip_id = %s "
            "ORDER BY l.position NULLS FIRST, i.day NULLS FIRST, i.position, i.id",
            (trip_id,),
        )
        return cur.fetchall()


def update_item(item_id: int, cost: Decimal, currency: str, day: int | None) -> None:
    """Edit an item's cost, currency, and day."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE items SET cost = %s, currency = %s, day = %s WHERE id = %s",
            (cost, currency, day, item_id),
        )


def delete_item(item_id: int) -> None:
    """Remove one item."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM items WHERE id = %s", (item_id,))
