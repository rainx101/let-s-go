"""Distance math + activity-anchored day grouping. Pure functions (no Streamlit/DB)
so they're unit-testable. Activities define the days; each restaurant joins the day
of its nearest activity, ordered by closeness (PRD §6/§8)."""

import math
from collections.abc import Sequence

Coord = tuple[float, float]
Activity = tuple[int, float, float, int | None]  # (item_id, lat, lon, fixed_day)
Resto = tuple[int, float, float]  # (item_id, lat, lon)
Placed = tuple[int, float | None]  # (item_id, distance_km to its day's anchor)

_EARTH_KM = 6371.0


def haversine(a: Coord, b: Coord) -> float:
    """Great-circle distance between two (lat, lon) points, in kilometres."""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_KM * math.asin(math.sqrt(h))


def plan_days(
    activities: Sequence[Activity],
    restaurants: Sequence[Resto],
    num_days: int,
    ref: Coord | None,
) -> list[list[Placed]]:
    """Group located items into `num_days` day-buckets, activity-first.

    Activities with a `fixed_day` (a day index, e.g. from a typed date) keep that
    day, clamped into range; undated activities spread one-per-day into the emptiest
    days. Each restaurant joins the day of its nearest activity, carrying its distance
    to that activity. With no activities at all, every restaurant lands on day 1 with
    its distance to `ref` (the hotel, else the stop anchor). Within a day, the anchor
    activities lead (distance None), then restaurants nearest-first. Empty days stay
    as empty buckets so the caller can still show them (with their dates)."""
    if num_days < 1:
        return []

    day_acts: list[list[Activity]] = [[] for _ in range(num_days)]
    undated: list[Activity] = []
    for act in activities:
        fixed = act[3]
        if fixed is None:
            undated.append(act)
        else:
            day_acts[min(max(fixed, 0), num_days - 1)].append(act)
    for act in undated:
        day = min(range(num_days), key=lambda d: (len(day_acts[d]), d))
        day_acts[day].append(act)

    located_acts = [(a, d) for d, acts in enumerate(day_acts) for a in acts]
    day_restos: list[list[Placed]] = [[] for _ in range(num_days)]
    if located_acts:
        for rid, rlat, rlon in restaurants:
            act, day = min(
                located_acts, key=lambda ad: haversine((rlat, rlon), (ad[0][1], ad[0][2]))
            )
            day_restos[day].append((rid, haversine((rlat, rlon), (act[1], act[2]))))
    else:
        for rid, rlat, rlon in restaurants:
            dist = haversine((rlat, rlon), ref) if ref is not None else None
            day_restos[0].append((rid, dist))

    out: list[list[Placed]] = []
    for d in range(num_days):
        row: list[Placed] = [(a[0], None) for a in day_acts[d]]
        row += sorted(day_restos[d], key=lambda p: math.inf if p[1] is None else p[1])
        out.append(row)
    return out
