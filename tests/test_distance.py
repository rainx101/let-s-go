"""Tests for distance math + activity-anchored day grouping (pure, no DB/network)."""

import pytest

from lets_go.distance import haversine, plan_days

# Rough anchor + points: two clustered near the anchor, two clustered ~5km east.
ANCHOR = (33.81, -117.92)  # Disneyland-ish
NEAR_A = (33.815, -117.921)
NEAR_B = (33.812, -117.918)
FAR_A = (33.81, -117.86)
FAR_B = (33.814, -117.861)


def test_haversine_zero_for_same_point():
    assert haversine(ANCHOR, ANCHOR) == 0.0


def test_haversine_known_distance_approx():
    # ~1 degree of latitude ≈ 111 km.
    assert 110 < haversine((0.0, 0.0), (1.0, 0.0)) < 112


def _ids(day):
    return {item_id for item_id, _ in day}


def test_plan_days_restaurant_joins_nearest_activity_day():
    # Disney on day 0, beach on day 1; each restaurant sits with the nearer one.
    acts = [(10, *ANCHOR, 0), (11, *FAR_A, 1)]
    restos = [(1, *NEAR_A), (2, *FAR_B)]
    plan = plan_days(acts, restos, num_days=2, ref=None)
    assert _ids(plan[0]) == {10, 1}  # Disney + its near restaurant
    assert _ids(plan[1]) == {11, 2}  # beach + its far restaurant


def test_plan_days_activity_is_anchor_with_no_distance():
    plan = plan_days([(10, *ANCHOR, 0)], [(1, *NEAR_A)], num_days=1, ref=None)
    assert plan[0][0] == (10, None)  # activity leads its day, no distance


def test_plan_days_restaurant_distance_is_to_its_nearest_activity():
    plan = plan_days([(10, *ANCHOR, 0)], [(1, *NEAR_A)], num_days=1, ref=None)
    _, dist = plan[0][1]
    assert dist == pytest.approx(haversine(NEAR_A, ANCHOR))


def test_plan_days_within_day_orders_restaurants_nearest_first():
    # Far listed before near; output puts the near one first.
    plan = plan_days([(10, *ANCHOR, 0)], [(2, *FAR_A), (1, *NEAR_A)], num_days=1, ref=None)
    order = [item_id for item_id, _ in plan[0]]
    assert order == [10, 1, 2]


def test_plan_days_undated_activity_lands_on_first_day_rest_empty():
    # 5-day trip, one undated activity: activity + restaurants on day 1, days 2-5 empty.
    plan = plan_days([(10, *ANCHOR, None)], [(1, *NEAR_A), (2, *FAR_A)], num_days=5, ref=None)
    assert _ids(plan[0]) == {10, 1, 2}
    assert plan[1:] == [[], [], [], []]


def test_plan_days_undated_activities_fill_separate_empty_days():
    plan = plan_days([(10, *ANCHOR, None), (11, *FAR_A, None)], [], num_days=5, ref=None)
    assert _ids(plan[0]) == {10}
    assert _ids(plan[1]) == {11}
    assert plan[2:] == [[], [], []]


def test_plan_days_no_activities_all_on_day_one_from_ref():
    # No activities to anchor: everything on day 1, distance measured from the ref (hotel).
    plan = plan_days([], [(2, *FAR_A), (1, *NEAR_A)], num_days=3, ref=ANCHOR)
    assert [item_id for item_id, _ in plan[0]] == [1, 2]  # near first, by distance from ref
    _, dist = plan[0][0]
    assert dist == pytest.approx(haversine(NEAR_A, ANCHOR))
    assert plan[1:] == [[], []]


def test_plan_days_no_activities_no_ref_keeps_items_without_distance():
    plan = plan_days([], [(1, *NEAR_A), (2, *FAR_A)], num_days=1, ref=None)
    assert plan[0] == [(1, None), (2, None)]


def test_plan_days_empty_returns_empty_day_buckets():
    assert plan_days([], [], num_days=3, ref=ANCHOR) == [[], [], []]


def test_plan_days_zero_days_returns_empty():
    assert plan_days([(10, *ANCHOR, 0)], [], num_days=0, ref=None) == []


def test_plan_days_fixed_day_beyond_range_clamps_into_last_day():
    plan = plan_days([(10, *ANCHOR, 9)], [], num_days=3, ref=None)
    assert _ids(plan[2]) == {10}
    assert plan[:2] == [[], []]
