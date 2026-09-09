"""Tests for budget math."""

from lets_go.budget import (
    budget_progress,
    flight_hotel_ceilings,
    is_over_budget,
    remaining_budget,
    total_spent,
)


def test_total_spent_sums_costs(sample_costs):
    assert total_spent(sample_costs) == 920.0


def test_total_spent_empty_is_zero():
    assert total_spent([]) == 0


def test_remaining_budget_under_cap(sample_costs):
    assert remaining_budget(2000.0, sample_costs) == 1080.0


def test_remaining_budget_can_go_negative(sample_costs):
    assert remaining_budget(900.0, sample_costs) == -20.0


def test_is_over_budget_true_when_exceeds_cap(sample_costs):
    assert is_over_budget(900.0, sample_costs) is True


def test_is_over_budget_false_when_within_cap(sample_costs):
    assert is_over_budget(2000.0, sample_costs) is False


def test_budget_progress_half_spent():
    assert budget_progress(1000.0, 500.0) == 0.5


def test_budget_progress_clamps_over_cap_to_one():
    assert budget_progress(1000.0, 1500.0) == 1.0


def test_budget_progress_zero_cap_is_full_when_spent():
    assert budget_progress(0.0, 50.0) == 1.0


def test_budget_progress_zero_cap_zero_spent_is_empty():
    assert budget_progress(0.0, 0.0) == 0.0


def test_ceilings_both_needed_no_caps_split_half():
    assert flight_hotel_ceilings(2000.0, None, None, True, True) == (1000.0, 1000.0)


def test_ceilings_only_hotel_takes_whole_budget():
    assert flight_hotel_ceilings(1000.0, None, None, False, True) == (None, 1000.0)


def test_ceilings_only_flight_takes_whole_budget():
    assert flight_hotel_ceilings(1000.0, None, None, True, False) == (1000.0, None)


def test_ceilings_flight_cap_leaves_rest_for_hotel():
    assert flight_hotel_ceilings(2000.0, 1200.0, None, True, True) == (1200.0, 800.0)


def test_ceilings_both_caps_are_used_as_is():
    assert flight_hotel_ceilings(2000.0, 900.0, 1000.0, True, True) == (900.0, 1000.0)


def test_ceilings_neither_needed_is_none():
    assert flight_hotel_ceilings(2000.0, None, None, False, False) == (None, None)
