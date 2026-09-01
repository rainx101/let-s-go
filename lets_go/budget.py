"""Budget math for a trip. Pure functions — no Streamlit or DB, so they're
easy to test. All amounts are assumed to already be in the trip's home currency
(PRD: single cap, whole trip, one home currency)."""


def total_spent(costs: list[float]) -> float:
    """Sum of all item costs in the home currency."""
    return sum(costs)


def remaining_budget(cap: float, costs: list[float]) -> float:
    """How much of the budget cap is left. Negative means over budget."""
    return cap - total_spent(costs)


def is_over_budget(cap: float, costs: list[float]) -> bool:
    """True when the planned costs exceed the cap."""
    return remaining_budget(cap, costs) < 0
