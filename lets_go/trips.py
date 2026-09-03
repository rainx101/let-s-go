"""Trips data layer: pure helpers (validation, date range) + DB access.
Pure helpers have no Streamlit/DB deps so they're unit-testable."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from psycopg.rows import dict_row

from lets_go.db import get_connection


@dataclass
class DraftLeg:
    """A city/leg being drafted in the UI before the trip is saved."""

    city: str
    country: str = ""
    start_date: date | None = None
    end_date: date | None = None
    need_flight: bool = False
    need_hotel: bool = False


# --- pure helpers (testable) ------------------------------------------------


def trip_date_range(legs: list[DraftLeg]) -> tuple[date | None, date | None]:
    """Earliest start and latest end across all legs (ignoring blanks)."""
    starts = [leg.start_date for leg in legs if leg.start_date]
    ends = [leg.end_date for leg in legs if leg.end_date]
    return (min(starts) if starts else None, max(ends) if ends else None)


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
        if leg.start_date and leg.end_date and leg.end_date < leg.start_date:
            errors.append(f"City {i}: end date is before start date.")
    return errors


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
) -> int:
    """Insert a trip and its legs atomically; return the new trip id."""
    conn = get_connection()
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            "INSERT INTO trips (name, home_currency, budget_cap) VALUES (%s, %s, %s) RETURNING id",
            (name.strip(), home_currency, budget_cap),
        )
        row = cur.fetchone()
        assert row is not None  # INSERT ... RETURNING always yields a row
        trip_id = row[0]
        for pos, leg in enumerate(legs):
            cur.execute(
                "INSERT INTO legs (trip_id, city, country, start_date, end_date, "
                "need_flight, need_hotel, position) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    trip_id,
                    leg.city.strip(),
                    leg.country.strip() or None,
                    leg.start_date,
                    leg.end_date,
                    leg.need_flight,
                    leg.need_hotel,
                    pos,
                ),
            )
    return trip_id


def list_trips() -> list[dict]:
    """All trips (newest first), each with a `legs` list attached."""
    conn = get_connection()
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, name, home_currency, budget_cap, created_at "
            "FROM trips ORDER BY created_at DESC"
        )
        trips = cur.fetchall()
        cur.execute(
            "SELECT trip_id, city, country, start_date, end_date, "
            "need_flight, need_hotel, position FROM legs ORDER BY position"
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
    day: int | None,
) -> int:
    """Insert one planned item (cost in the trip's home currency); return its id."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO items (trip_id, leg_id, category, name, cost, day) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (trip_id, leg_id, category, name.strip(), cost, day),
        )
        row = cur.fetchone()
        assert row is not None  # INSERT ... RETURNING always yields a row
        return row[0]


def list_items(trip_id: int) -> list[dict]:
    """All items for a trip, ordered by leg, then day, then position."""
    conn = get_connection()
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT i.id, i.leg_id, i.category, i.name, i.cost, i.day, i.position "
            "FROM items i LEFT JOIN legs l ON l.id = i.leg_id "
            "WHERE i.trip_id = %s "
            "ORDER BY l.position NULLS FIRST, i.day NULLS FIRST, i.position, i.id",
            (trip_id,),
        )
        return cur.fetchall()


def delete_item(item_id: int) -> None:
    """Remove one item."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM items WHERE id = %s", (item_id,))
