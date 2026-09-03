"""Tests for budget math."""

from lets_go.budget import budget_progress, is_over_budget, remaining_budget, total_spent


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
