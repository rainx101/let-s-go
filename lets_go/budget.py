"""Budget math for a trip. Pure functions — no Streamlit or DB, so they're
easy to test. All amounts are assumed to already be in the trip's home currency."""

from typing import NamedTuple


class FlightHotelCeilings(NamedTuple):
    """Per-item search ceilings from a city's flight+hotel budget (PRD §6).
    A field is None when that item isn't needed for the stop."""

    flight: float | None
    hotel: float | None


def total_spent(costs: list[float]) -> float:
    """Sum of all item costs in the home currency."""
    return sum(costs)


def remaining_budget(cap: float, costs: list[float]) -> float:
    """How much of the budget cap is left. Negative means over budget."""
    return cap - total_spent(costs)


def is_over_budget(cap: float, costs: list[float]) -> bool:
    """True when the planned costs exceed the cap."""
    return remaining_budget(cap, costs) < 0


def budget_progress(cap: float, spent: float) -> float:
    """Fraction of the cap used, clamped to 0.0–1.0 for a progress bar.
    With no cap set, it reads full whenever anything is spent."""
    if cap <= 0:
        return 1.0 if spent > 0 else 0.0
    return min(spent / cap, 1.0)


def flight_hotel_ceilings(
    budget: float,
    flight_cap: float | None,
    hotel_cap: float | None,
    need_flight: bool,
    need_hotel: bool,
) -> FlightHotelCeilings:
    """Split a city's flight+hotel budget into per-item search ceilings (PRD §6).

    A set cap wins. Otherwise: if only one of flight/hotel is needed it takes the
    whole budget; if both are needed the (un-capped) side gets what's left after
    the capped one, or half each when neither is capped. Not-needed → None."""
    if not need_flight and not need_hotel:
        return FlightHotelCeilings(None, None)
    if need_flight and not need_hotel:
        return FlightHotelCeilings(flight_cap if flight_cap is not None else budget, None)
    if need_hotel and not need_flight:
        return FlightHotelCeilings(None, hotel_cap if hotel_cap is not None else budget)
    if flight_cap is not None and hotel_cap is not None:
        return FlightHotelCeilings(flight_cap, hotel_cap)
    if flight_cap is not None:
        return FlightHotelCeilings(flight_cap, max(budget - flight_cap, 0.0))
    if hotel_cap is not None:
        return FlightHotelCeilings(max(budget - hotel_cap, 0.0), hotel_cap)
    half = budget / 2
    return FlightHotelCeilings(half, half)
