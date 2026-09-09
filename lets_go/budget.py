"""Budget math for a trip. Pure functions — no Streamlit or DB, so they're
easy to test. All amounts are assumed to already be in the trip's home currency
(PRD: single cap, whole trip, one home currency)."""

from typing import NamedTuple


class WaterfallBudget(NamedTuple):
    """The three stage figures of the waterfall (PRD §6)."""

    after_activities: float  # cap - activities; the true (maybe negative) overage
    flight_hotel_alloc: float  # chosen amount, clamped to what's left after activities
    food_remainder: float  # what's left for food after the flight+hotel allocation


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


def flight_hotel_default(city_budget: float) -> float:
    """A city's default flight+hotel budget = half its budget (PRD §6). The user
    can override it; the Phase 3 hotel search obeys the result as its ceiling."""
    return city_budget / 2


def waterfall_budget(
    cap: float, activities_spent: float, flight_hotel_alloc: float
) -> WaterfallBudget:
    """Split the cap in flow order (PRD §6): activities off the top, then the
    chosen flight+hotel allocation, then food gets the remainder. The allocation
    is clamped to what's actually left after activities."""
    after_activities = cap - activities_spent
    usable = max(after_activities, 0.0)
    alloc = min(max(flight_hotel_alloc, 0.0), usable)
    return WaterfallBudget(after_activities, alloc, usable - alloc)
