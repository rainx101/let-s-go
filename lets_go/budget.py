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


def budget_progress(cap: float, spent: float) -> float:
    """Fraction of the cap used, clamped to 0.0–1.0 for a progress bar.
    With no cap set, it reads full whenever anything is spent."""
    if cap <= 0:
        return 1.0 if spent > 0 else 0.0
    return min(spent / cap, 1.0)
