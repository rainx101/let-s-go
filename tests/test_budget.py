"""Tests for budget math."""

from lets_go.budget import (
    budget_progress,
    flight_hotel_default,
    is_over_budget,
    remaining_budget,
    total_spent,
    waterfall_budget,
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


def test_waterfall_splits_after_activities():
    # 2000 cap, 500 activities -> 1500 left; choose 900 for flight+hotel -> 600 food
    wb = waterfall_budget(2000.0, 500.0, 900.0)
    assert wb.after_activities == 1500.0
    assert wb.flight_hotel_alloc == 900.0
    assert wb.food_remainder == 600.0


def test_waterfall_allocation_clamped_to_whats_left():
    # asking 2000 for flight+hotel when only 1500 is left caps it at 1500, food 0
    wb = waterfall_budget(2000.0, 500.0, 2000.0)
    assert wb.flight_hotel_alloc == 1500.0
    assert wb.food_remainder == 0.0


def test_waterfall_no_allocation_leaves_all_for_food():
    wb = waterfall_budget(2000.0, 500.0, 0.0)
    assert wb.flight_hotel_alloc == 0.0
    assert wb.food_remainder == 1500.0


def test_flight_hotel_default_is_half_the_city_budget():
    assert flight_hotel_default(2000.0) == 1000.0


def test_waterfall_activities_over_cap_zeroes_the_rest():
    # activities blew the cap: after_activities is the true (negative) overage,
    # but nothing is usable for flight+hotel or food
    wb = waterfall_budget(1000.0, 1200.0, 300.0)
    assert wb.after_activities == -200.0
    assert wb.flight_hotel_alloc == 0.0
    assert wb.food_remainder == 0.0
