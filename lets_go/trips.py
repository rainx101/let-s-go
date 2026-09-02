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
