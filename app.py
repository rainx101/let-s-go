"""let's go — travel budget & planning app."""

from datetime import date, timedelta
from decimal import Decimal

import streamlit as st

from lets_go.auth import require_login
from lets_go.budget import (
    FlightHotelCeilings,
    budget_progress,
    flight_hotel_ceilings,
    is_over_budget,
    remaining_budget,
    total_spent,
)
from lets_go.currency import convert, currency_for_country, live_rates_or_static
from lets_go.db import health_check, init_db
from lets_go.distance import haversine, plan_days
from lets_go.geocoding import build_query, geocode_or_none, place_query, search_or_empty
from lets_go.trips import (
    DraftLeg,
    add_item,
    add_leg,
    create_trip,
    dates_overlap,
    delete_item,
    delete_leg,
    delete_trip,
    destination_budgets,
    export_json,
    leg_endpoint,
    list_items,
    list_trips,
    normalize_place,
    reorder_items,
    set_item_location,
    set_leg_anchor,
    set_leg_cap,
    set_trip_status,
    update_item,
    update_leg,
    update_trip,
    validate_budget_caps,
    validate_new_item,
    validate_new_trip,
)

st.set_page_config(page_title="let's go", page_icon="🧳", layout="centered")

require_login()
init_db()

st.title("🧳 let's go")

with st.sidebar:
    st.caption("Database")
    if health_check():
        st.success("Neon connected", icon="✅")

CURRENCIES = ["USD", "EUR", "JPY", "GBP", "AUD", "CAD", "TWD", "KRW", "THB", "CNY", "IDR"]
CATEGORY_ICON = {"flight": "✈️", "hotel": "🏨", "spot": "📍", "restaurant": "🍽️"}
CATEGORY_LABEL = {
    "spot": "Activity",
    "flight": "Flight",
    "hotel": "Hotel",
    "restaurant": "Restaurant",
}
ALL_CATEGORIES = ["spot", "flight", "hotel", "restaurant"]

# The budget covers flight + hotel; activities and food are extras added on top
# (PRD §6). Each step adds one category; flight/hotel steps show only when needed.
STEP_TITLE = {"flight": "Flight", "hotel": "Hotel", "spot": "Activities", "restaurant": "Food"}


def _leg_steps(leg: dict) -> list[str]:
    """Wizard step categories for a stop: Flight/Hotel only when needed, then the
    Activities and Food extras."""
    steps = []
    if leg["need_flight"]:
        steps.append("flight")
    if leg["need_hotel"]:
        steps.append("hotel")
    return [*steps, "spot", "restaurant"]


plan_tab, receipts_tab, restaurants_tab = st.tabs(["Plan", "Receipts", "Restaurants by city"])

trips = list_trips()


def _range_bounds(legs: list[dict]) -> tuple[object, object]:
    starts = [leg["start_date"] for leg in legs if leg["start_date"]]
    ends = [leg["end_date"] for leg in legs if leg["end_date"]]
    return (min(starts) if starts else None, max(ends) if ends else None)


@st.cache_data(ttl=3600)
def _rates() -> dict[str, Decimal]:
    """Live USD-per-unit rates (cached 1h), or the static fallback table."""
    return live_rates_or_static()


@st.cache_data(ttl=86400)
def _geocode(query: str) -> tuple[float, float] | None:
    """Anchor coordinates for a place (cached a day; one Nominatim call per
    query), or None on no match / any failure — the UI then keeps manual entry."""
    return geocode_or_none(query)


@st.cache_data(ttl=86400)
def _place_search(query: str) -> list[dict]:
    """Top place matches to pick from (cached; one Nominatim call per query)."""
    return search_or_empty(query)


def _locate(query: str) -> tuple[float, float, str] | None:
    """Top match as (lat, lon, address), or None — the address is stored so the
    day plan can show where a spot/restaurant is. Reuses the cached place search."""
    matches = _place_search(query)
    if not matches:
        return None
    top = matches[0]
    return (top["lat"], top["lon"], top["display_name"])


def _home_amount(item: dict, home: str) -> Decimal:
    if item["cost"] is None:  # TBD — counts as 0 until a price is filled in
        return Decimal(0)
    return convert(item["cost"], item["currency"] or home, home, rates=_rates())


# --- items (shared by the guided steps and the finalized receipt) ------------


def _submit_item_cb(
    tid: int, categories: list[str], kp: str, fixed_leg_id: int | None, place: tuple[str, str]
) -> None:
    g = st.session_state
    name = g[kp + "name"]
    cost = g[kp + "cost"]  # None = TBD (a place with no price yet)
    category = categories[0] if len(categories) == 1 else g[kp + "type"]
    errors = validate_new_item(name, cost if cost is not None else 0)
    if errors:
        g[kp + "err"] = errors
        return
    amount = Decimal(str(cost)) if cost is not None else None
    new_id = add_item(tid, fixed_leg_id, category, name, amount, g[kp + "ccy"], g[kp + "date"])
    if category in ("spot", "restaurant") and (place[0] or place[1]):
        found = _locate(place_query(name, place[0], place[1]))  # locate the place you typed
        if found:
            set_item_location(new_id, found[0], found[1], found[2])
    g[kp + "err"] = []
    g[kp + "name"] = ""
    g[kp + "cost"] = None  # keep the date so several items can share a day


def _save_item_loc_cb(item_id: int, lat_key: str, lon_key: str) -> None:
    set_item_location(item_id, st.session_state.get(lat_key), st.session_state.get(lon_key))


def _item_location_editor(it: dict, place: tuple[str, str]) -> None:
    """Place-first location for one activity/restaurant — the point used to plan
    the day by closeness to the anchor (PRD §6/§8). Located from the name when
    added; the raw coordinates live under 'Adjust' for the rare miss (§11)."""
    iid = it["id"]
    lat_key, lon_key = f"iloclat_{iid}", f"iloclon_{iid}"
    located = it.get("lat") is not None
    near = f" near {place[0]}" if place[0] else ""
    st.caption(f"📍 Located{near} — grouped nearby." if located else "📍 Not located yet.")
    with st.expander("Adjust location", expanded=not located):
        _coord_inputs(
            float(it["lat"]) if it.get("lat") is not None else None,
            float(it["lon"]) if it.get("lon") is not None else None,
            (lat_key, lon_key),
            _save_item_loc_cb,
            (iid, lat_key, lon_key),
        )
        if st.button("Locate from name", key=f"iloc_{iid}"):
            found = _locate(place_query(it["name"], place[0], place[1]))
            if found is None:
                st.warning("Couldn't find that place — enter the coordinates by hand.")
            else:
                set_item_location(iid, found[0], found[1], found[2])
                st.session_state.pop(lat_key, None)  # reseed inputs from the stored value
                st.session_state.pop(lon_key, None)
                st.rerun()


def _item_row(
    it: dict,
    home: str,
    leg_label: dict,
    leg_dates: dict,
    leg_place: dict,
    show_where: bool = True,
) -> None:
    row, edit, remove = st.columns([6, 1, 1])
    icon = CATEGORY_ICON.get(it["category"], "")
    where = f" · {leg_label.get(it['leg_id'], 'General')}" if show_where else ""
    when = f" · {it['on_date']}" if it.get("on_date") else ""
    est = " (est.)" if it["category"] == "restaurant" else ""
    ccy = it["currency"] or home
    if it["cost"] is None:
        price = "_TBD_"
    else:
        converted = f" ≈ {_home_amount(it, home)} {home}" if ccy != home else ""
        price = f"{it['cost']} {ccy}{converted}"
    row.write(f"{icon} **{it['name']}** — {price}{est}{where}{when}")
    lo, hi = leg_dates.get(it["leg_id"], (None, None))
    with edit.popover("✏️"):
        new_cost = st.number_input(
            "Cost (blank = TBD)",
            value=float(it["cost"]) if it["cost"] is not None else None,
            min_value=0.0,
            step=10.0,
            placeholder="e.g. 40",
            key=f"icost_{it['id']}",
        )
        new_ccy = st.selectbox(
            "Currency",
            CURRENCIES,
            index=CURRENCIES.index(ccy) if ccy in CURRENCIES else 0,
            key=f"iccy_{it['id']}",
        )
        new_date = st.date_input(
            "Date", value=it.get("on_date"), min_value=lo, max_value=hi, key=f"idate_{it['id']}"
        )
        if st.button("Save", key=f"isave_{it['id']}"):
            amount = Decimal(str(new_cost)) if new_cost is not None else None
            update_item(it["id"], amount, new_ccy, new_date)
            st.rerun()
        if it["category"] in ("spot", "restaurant"):
            st.divider()
            _item_location_editor(it, leg_place.get(it["leg_id"], ("", "")))
    if remove.button("✕", key=f"rm_item_{it['id']}"):
        delete_item(it["id"])
        st.rerun()


def _item_manager(
    trip: dict,
    show_add: bool,
    tag: str,
    categories: list[str] = ALL_CATEGORIES,
    fixed_leg_id: int | None = None,
) -> None:
    """List a trip's items and (optionally) add. With `fixed_leg_id`, scope to
    that one destination (all categories); otherwise filter by `categories`."""
    tid = trip["id"]
    legs = trip["legs"]
    home = trip["home_currency"]
    leg_label = {leg["id"]: leg["city"] for leg in legs}
    leg_dates = {leg["id"]: (leg["start_date"], leg["end_date"]) for leg in legs}
    leg_place = {leg["id"]: (leg["city"], leg["country"] or "") for leg in legs}
    items = list_items(tid)
    if fixed_leg_id is not None:
        items = [it for it in items if it["leg_id"] == fixed_leg_id]
    items = [it for it in items if it["category"] in categories]

    if items:
        for it in items:
            _item_row(it, home, leg_label, leg_dates, leg_place, show_where=fixed_leg_id is None)
    else:
        st.caption("Nothing added yet.")

    if not show_add:
        return

    kp = f"add_{tag}_{tid}_"
    st.session_state.setdefault(kp + "err", [])
    st.session_state.setdefault(kp + "cost", None)  # empty by default; no value= (avoids a warning)
    st.markdown("**Add**")
    pc1, pc2 = st.columns([3, 1])
    item_cost = pc1.number_input(
        "Cost (blank = TBD)", min_value=0.0, step=10.0, placeholder="e.g. 40", key=kp + "cost"
    )
    item_ccy = pc2.selectbox(
        "Currency",
        CURRENCIES,
        index=CURRENCIES.index(home) if home in CURRENCIES else 0,
        key=kp + "ccy",
    )
    if item_cost and item_ccy != home:
        st.caption(f"≈ {convert(Decimal(str(item_cost)), item_ccy, home, rates=_rates())} {home}")
    if len(categories) > 1:
        st.selectbox("Type", categories, format_func=lambda c: CATEGORY_LABEL[c], key=kp + "type")
    st.text_input("Name", key=kp + "name")
    lo, hi = leg_dates.get(fixed_leg_id, (None, None))
    st.date_input("Date (optional)", value=None, min_value=lo, max_value=hi, key=kp + "date")
    st.button(
        "Add",
        key=kp + "btn",
        on_click=_submit_item_cb,
        args=(tid, categories, kp, fixed_leg_id, leg_place.get(fixed_leg_id, ("", ""))),
    )
    for err in st.session_state[kp + "err"]:
        st.error(err)


def _legs_summary(legs: list[dict]) -> None:
    for leg in legs:
        arrow = "⇄" if leg.get("round_trip") else "→"
        origin = f"{leg['from_city']} {arrow} " if leg.get("from_city") else ""
        place = f"{origin}**{leg['city']}**" + (f", {leg['country']}" if leg["country"] else "")
        flags = ("✈️" if leg["need_flight"] else "") + ("🏨" if leg["need_hotel"] else "")
        cap = f" · cap {leg['budget_cap']}" if leg.get("budget_cap") is not None else ""
        span = f"{leg['start_date'] or '?'} → {leg['end_date'] or '?'}"
        st.write(f"- {place} · {span}{cap} {flags}")


def _budget_line(spent: float, cap: Decimal | None, home: str, label: str = "Spent") -> None:
    """One budget line — a progress bar + spent/left when a cap is set, else the
    spent total. Used for the whole trip and for a single destination."""
    if cap is not None and float(cap) > 0:
        cap_f = float(cap)
        st.progress(budget_progress(cap_f, spent))
        left = remaining_budget(cap_f, [spent])
        msg = f"{label}: {spent:,.2f} / {cap_f:,.2f} {home} · {left:,.2f} left"
        if is_over_budget(cap_f, [spent]):
            st.error(f"{msg} — over budget")
        else:
            st.caption(msg)
    else:
        st.caption(f"{label}: {spent:,.2f} {home}")


def _stage_spent(items: list[dict], home: str, categories: set[str]) -> float:
    return total_spent(
        [float(_home_amount(it, home)) for it in items if it["category"] in categories]
    )


def _leg_ceilings(trip: dict, leg: dict) -> FlightHotelCeilings:
    """This stop's flight/hotel search ceilings from its flight+hotel budget."""
    budget = _stop_budget(trip, leg)  # the stop's budget IS the flight+hotel budget
    if budget is None or float(budget) <= 0:
        return FlightHotelCeilings(None, None)
    fc, hc = leg.get("flight_cap"), leg.get("hotel_cap")
    return flight_hotel_ceilings(
        float(budget),
        float(fc) if fc is not None else None,
        float(hc) if hc is not None else None,
        leg["need_flight"],
        leg["need_hotel"],
    )


def _city_budget_bar(trip: dict, leg: dict, items: list[dict], home: str) -> None:
    """Budget = flight + hotel (with per-item ceilings); activities & food are
    extras shown on top, not capped (PRD §6)."""
    leg_items = [it for it in items if it["leg_id"] == leg["id"]]
    budget = _stop_budget(trip, leg)
    ceil = _leg_ceilings(trip, leg)
    stages = []
    if ceil.flight is not None:
        stages.append(("✈️ Flight", _stage_spent(leg_items, home, {"flight"}), ceil.flight))
    if ceil.hotel is not None:
        stages.append(("🏨 Hotel", _stage_spent(leg_items, home, {"hotel"}), ceil.hotel))
    if budget is not None and float(budget) > 0:
        st.caption(f"✈️🏨 **Flight + hotel budget: {float(budget):,.0f} {home}**")
    if stages:
        for col, (label, spent, ceiling) in zip(st.columns(len(stages)), stages, strict=True):
            with col:
                _budget_line(spent, Decimal(str(ceiling)), home, label)
    activities = _stage_spent(leg_items, home, {"spot"})
    food = _stage_spent(leg_items, home, {"restaurant"})
    st.caption(
        f"➕ Extras (on top, not capped): 🎯 {activities:,.0f} · 🍽️ {food:,.0f} "
        f"= **{activities + food:,.0f} {home}**"
    )


def _save_leg_cap_cb(leg_id: int, field: str, key: str) -> None:
    raw = st.session_state.get(key)
    set_leg_cap(leg_id, field, Decimal(str(raw)) if raw is not None else None)


def _cap_input(trip: dict, leg: dict, field: str) -> None:
    """Optional flight/hotel cap for this stop; blank = the split default shown."""
    budget = _stop_budget(trip, leg)
    if budget is None or float(budget) <= 0:
        return
    which = "Flight" if field == "flight_cap" else "Hotel"
    ceil = _leg_ceilings(trip, leg)
    default = ceil.flight if field == "flight_cap" else ceil.hotel
    stored = leg.get(field)
    key = f"legcap_{field}_{leg['id']}"
    st.number_input(
        f"{which} budget cap — blank uses {default:,.0f} {trip['home_currency']}",
        min_value=0.0,
        value=float(stored) if stored is not None else None,
        placeholder=f"{default:,.0f}",
        key=key,
        on_change=_save_leg_cap_cb,
        args=(leg["id"], field, key),
    )


def _stop_budget(trip: dict, leg: dict) -> Decimal | None:
    """This destination's budget in home currency (its own cap, else an even
    share of what's left) — see destination_budgets."""
    legs = trip["legs"]
    budgets = destination_budgets(trip["budget_cap"], [_draftleg_from_row(leg_) for leg_ in legs])
    idx = next(i for i, leg_ in enumerate(legs) if leg_["id"] == leg["id"])
    return budgets[idx]


def _budget_summary(trip: dict, home: str) -> None:
    """Whole-trip budget = flight + hotel spent vs the flight+hotel budget, with
    activities + food shown as extras on top (PRD §6). Used by Review and Receipts."""
    items = list_items(trip["id"])
    fh_spent = _stage_spent(items, home, {"flight", "hotel"})
    extras = _stage_spent(items, home, {"spot", "restaurant"})
    total_budget = sum(float(_stop_budget(trip, leg) or 0) for leg in trip["legs"])
    _budget_line(
        fh_spent,
        Decimal(str(total_budget)) if total_budget > 0 else None,
        home,
        "✈️🏨 Flight + hotel",
    )
    st.caption(
        f"➕ Extras (activities + food): {extras:,.2f} {home}  ·  "
        f"Trip total {fh_spent + extras:,.2f} {home}"
    )


def _render_receipt(trip: dict) -> None:
    """Read-only view of a finalized trip — the plan + budget. Editing happens in
    the Plan tab (see the finalized section's Edit action)."""
    home = trip["home_currency"]
    _legs_summary(trip["legs"])
    _budget_summary(trip, home)
    _item_manager(trip, show_add=False, tag=f"view{trip['id']}")


def _delete_trip_control(trip: dict) -> None:
    tid = trip["id"]
    confirm_key = f"confirm_del_{tid}"  # per-trip so one delete can't affect another
    if st.session_state.get(confirm_key):
        st.warning(f"Permanently delete **{trip['name']}** and everything in it?")
        yes, no = st.columns(2)
        if yes.button("Yes, delete", key=f"yesdel_{tid}"):
            if st.session_state.get("active_trip_id") == tid:
                st.session_state.active_trip_id = None
            delete_trip(tid)
            st.session_state[confirm_key] = False
            st.rerun()
        if no.button("Cancel", key=f"canceldel_{tid}"):
            st.session_state[confirm_key] = False
            st.rerun()
    elif st.button("🗑 Delete trip", key=f"askdel_{tid}"):
        st.session_state[confirm_key] = True
        st.rerun()


# --- one destination (leg) form, shared by the skeleton and the steps ---------


def _leg_field_defaults(prefix: str) -> dict:
    today = date.today()
    return {
        f"{prefix}from_city": "",
        f"{prefix}from_country": "",
        f"{prefix}city": "",
        f"{prefix}country": "",
        f"{prefix}start": today,
        f"{prefix}end": today + timedelta(days=1),
        f"{prefix}cap": None,
        f"{prefix}flight": False,
        f"{prefix}hotel": False,
        f"{prefix}round": False,
    }


def _place_picker(prefix: str) -> None:
    """Search a place and pick the exact match — fills the To city/Country below
    with the right name + country (disambiguates, fixes spelling)."""
    sc1, sc2 = st.columns([3, 1])
    sc1.text_input("🔎 Search a place", key=f"{prefix}q", placeholder="e.g. Disneyland, Anaheim")
    sc2.markdown("<div style='height:1.7em'></div>", unsafe_allow_html=True)
    if sc2.button("Search", key=f"{prefix}search"):
        st.session_state[f"{prefix}results"] = _place_search(st.session_state.get(f"{prefix}q", ""))
    results = st.session_state.get(f"{prefix}results")
    if results is None:
        return
    if not results:
        st.caption("No matches — type the city and country by hand below.")
        return
    labels = [r["display_name"] for r in results]
    pick = st.selectbox(
        "Matches", range(len(results)), format_func=lambda i: labels[i], key=f"{prefix}pick"
    )
    if st.button("Use this place", key=f"{prefix}use"):
        chosen = results[pick]
        st.session_state[f"{prefix}city"] = chosen["city"]
        st.session_state[f"{prefix}country"] = chosen["country"]
        st.session_state[f"{prefix}results"] = None
        st.rerun()


def _leg_field_widgets(prefix: str) -> None:
    oc1, oc2 = st.columns(2)
    oc1.text_input("From city (optional)", key=f"{prefix}from_city")
    oc2.text_input("From country (optional)", key=f"{prefix}from_country")
    _place_picker(prefix)
    tc1, tc2 = st.columns(2)
    tc1.text_input("To city", key=f"{prefix}city")
    tc2.text_input("Country (optional)", key=f"{prefix}country")
    st.checkbox("Round trip (return to the From city)", key=f"{prefix}round")
    dc1, dc2 = st.columns(2)
    dc1.date_input("Start date", key=f"{prefix}start")
    dc2.date_input("End date", key=f"{prefix}end")
    st.number_input(
        "Flight + hotel budget for this stop (optional)",
        min_value=0.0,
        step=100.0,
        placeholder="e.g. 500",
        key=f"{prefix}cap",
    )
    fc, hc = st.columns(2)
    fc.checkbox("Need flight", key=f"{prefix}flight")
    hc.checkbox("Need hotel", key=f"{prefix}hotel")


def _draftleg_from(prefix: str) -> DraftLeg:
    g = st.session_state
    return DraftLeg(
        city=normalize_place(g[f"{prefix}city"]),
        country=g[f"{prefix}country"].strip(),
        from_city=normalize_place(g[f"{prefix}from_city"]),
        from_country=g[f"{prefix}from_country"].strip(),
        start_date=g[f"{prefix}start"],
        end_date=g[f"{prefix}end"],
        need_flight=g[f"{prefix}flight"],
        need_hotel=g[f"{prefix}hotel"],
        round_trip=g[f"{prefix}round"],
        budget_cap=Decimal(str(g[f"{prefix}cap"])) if g[f"{prefix}cap"] else None,
    )


def _draftleg_from_row(leg: dict) -> DraftLeg:
    return DraftLeg(
        city=leg["city"],
        country=leg.get("country") or "",
        from_city=leg.get("from_city") or "",
        from_country=leg.get("from_country") or "",
        start_date=leg["start_date"],
        end_date=leg["end_date"],
        need_flight=leg["need_flight"],
        need_hotel=leg["need_hotel"],
        round_trip=leg.get("round_trip", False),
        budget_cap=leg.get("budget_cap"),
    )


def _seed_leg_fields(prefix: str, leg: DraftLeg) -> None:
    today = date.today()
    g = st.session_state
    g[f"{prefix}from_city"] = leg.from_city
    g[f"{prefix}from_country"] = leg.from_country
    g[f"{prefix}city"] = leg.city
    g[f"{prefix}country"] = leg.country
    g[f"{prefix}start"] = leg.start_date or today
    g[f"{prefix}end"] = leg.end_date or today + timedelta(days=1)
    g[f"{prefix}flight"] = leg.need_flight
    g[f"{prefix}hotel"] = leg.need_hotel
    g[f"{prefix}round"] = leg.round_trip
    g[f"{prefix}cap"] = float(leg.budget_cap) if leg.budget_cap else None


def _auto_locate(query: str) -> tuple[float, float] | None:
    """Geocode a place once per query per session (cached), so it resolves quietly
    from the name without the user clicking. None on no match / a repeat attempt."""
    if not query:
        return None
    tried = st.session_state.setdefault("geo_tried", set())
    if query in tried:
        return None
    tried.add(query)
    return _geocode(query)


def _save_anchor_cb(leg_id: int, lat_key: str, lon_key: str) -> None:
    lat = st.session_state.get(lat_key)
    lon = st.session_state.get(lon_key)
    set_leg_anchor(leg_id, lat, lon)


def _coord_inputs(lat: float | None, lon: float | None, keys, save_cb, args) -> None:
    """The raw lat/lon fallback pair — the manual override behind 'Adjust'."""
    lat_key, lon_key = keys
    c1, c2 = st.columns(2)
    c1.number_input(
        "Latitude",
        min_value=-90.0,
        max_value=90.0,
        value=lat,
        format="%.5f",
        key=lat_key,
        on_change=save_cb,
        args=args,
    )
    c2.number_input(
        "Longitude",
        min_value=-180.0,
        max_value=180.0,
        value=lon,
        format="%.5f",
        key=lon_key,
        on_change=save_cb,
        args=args,
    )


def _anchor_row(leg: dict) -> None:
    """The stop's map anchor — hotels are searched in a wide range around it and
    activities are planned near it (PRD §6/§7). Located automatically from the
    place name; the raw coordinates live under 'Adjust' for the rare miss (§11)."""
    lid = leg["id"]
    if leg.get("anchor_lat") is None:
        coords = _auto_locate(build_query(leg["city"], leg.get("country") or ""))
        if coords:
            set_leg_anchor(lid, coords[0], coords[1])
            leg["anchor_lat"], leg["anchor_lon"] = coords  # reflect it this render
    located = leg.get("anchor_lat") is not None
    if located:
        st.caption(f"📍 **{leg['city']}** located — hotels & activities plan around here.")
    else:
        st.caption(f"📍 Couldn't locate “{leg['city']}” — set it under **Adjust location**.")
    lat_key, lon_key = f"anchorlat_{lid}", f"anchorlon_{lid}"
    with st.expander("Adjust location", expanded=not located):
        _coord_inputs(
            float(leg["anchor_lat"]) if leg.get("anchor_lat") is not None else None,
            float(leg["anchor_lon"]) if leg.get("anchor_lon") is not None else None,
            (lat_key, lon_key),
            _save_anchor_cb,
            (lid, lat_key, lon_key),
        )
        if st.button("Locate from place name", key=f"anchorloc_{lid}"):
            coords = _geocode(build_query(leg["city"], leg.get("country") or ""))
            if coords is None:
                st.warning("Couldn't find that place — enter the coordinates by hand.")
            else:
                set_leg_anchor(lid, coords[0], coords[1])
                st.session_state.pop(lat_key, None)  # reseed inputs from the stored value
                st.session_state.pop(lon_key, None)
                st.rerun()


def _leg_header(leg: dict) -> None:
    """Read-only destination line: origin ⇄/→ city, country, and dates."""
    arrow = "⇄" if leg.get("round_trip") else "→"
    origin = f"{leg['from_city']} {arrow} " if leg.get("from_city") else ""
    place = f"{origin}**{leg['city']}**" + (f", {leg['country']}" if leg["country"] else "")
    st.markdown(place)
    st.caption(f"{leg['start_date'] or '?'} → {leg['end_date'] or '?'}")


def _reset_plan_ui() -> None:
    """Clear transient per-leg / setup widget state so nothing (an open edit form,
    a stale destination pick) carries over between planning sessions."""
    g = st.session_state
    prefixes = ("editleg_", "delleg_", "legerr_", "legcap_", "su_", "suadd_")
    for k in [k for k in g if k.startswith(prefixes)]:
        del g[k]
    for k in ("plan_dest", "plan_step", "plan_review"):
        g.pop(k, None)


def _destination_card(trip: dict, leg: dict) -> None:
    """One destination's header with in-place Edit / Delete (with confirm)."""
    legs = trip["legs"]
    lid = leg["id"]
    prefix = f"leg{lid}_"
    edit_key = f"editleg_{lid}"
    del_key = f"delleg_{lid}"
    if st.session_state.get(edit_key):
        _leg_field_widgets(prefix)
        for e in st.session_state.get(f"legerr_{lid}", []):
            st.warning(e)
        c1, c2 = st.columns(2)
        if c1.button("Save changes", key=f"savleg_{lid}", type="primary"):
            edited = _draftleg_from(prefix)
            others = [_draftleg_from_row(o) for o in legs if o["id"] != lid]
            problems = validate_new_trip("_", [edited])
            if any(dates_overlap(edited, o) for o in others):
                problems.append("Dates overlap with another destination.")
            if problems:
                st.session_state[f"legerr_{lid}"] = problems
            else:
                update_leg(lid, edited)
                st.session_state[edit_key] = False
                st.session_state[f"legerr_{lid}"] = []
            st.rerun()
        if c2.button("Cancel", key=f"cnlleg_{lid}"):
            st.session_state[edit_key] = False
            st.session_state[f"legerr_{lid}"] = []
            st.rerun()
        return
    _leg_header(leg)
    c1, c2 = st.columns(2)
    if c1.button("✏️ Edit destination", key=f"edleg_{lid}"):
        _seed_leg_fields(prefix, _draftleg_from_row(leg))
        st.session_state[edit_key] = True
        st.rerun()
    if st.session_state.get(del_key):
        st.warning("Delete this destination and its items?")
        d1, d2 = st.columns(2)
        if d1.button("Yes, delete", key=f"yesdelleg_{lid}"):
            delete_leg(lid)
            st.session_state[del_key] = False
            st.rerun()
        if d2.button("Cancel", key=f"cnldelleg_{lid}"):
            st.session_state[del_key] = False
            st.rerun()
    elif c2.button("🗑 Delete destination", key=f"delbtn_{lid}"):
        st.session_state[del_key] = True
        st.rerun()


# --- trip setup (edit name/budget/destinations before planning) --------------


def _save_setup_details(trip: dict) -> bool:
    """Persist the setup name / currency / budget; return False (with errors set)
    when the name is blank or the budget cap is missing."""
    tid = trip["id"]
    name = st.session_state.get(f"su_name_{tid}", trip["name"])
    ccy = st.session_state.get(f"su_ccy_{tid}", trip["home_currency"])
    raw = st.session_state.get(f"su_budget_{tid}")
    cap = Decimal(str(raw)) if raw else None
    errors: list[str] = []
    if not name.strip():
        errors.append("Trip needs a name.")
    if cap is None:
        errors.append("Set a flight + hotel budget for the trip.")
    if errors:
        st.session_state["su_errors"] = errors
        return False
    update_trip(tid, name, ccy, cap)
    st.session_state["su_errors"] = []
    return True


def _render_trip_setup(trip: dict) -> None:
    """Skeleton-style view for an existing trip: edit its name, currency, budget,
    and destinations, then Start planning to enter the per-destination steps."""
    tid = trip["id"]
    st.session_state.setdefault(f"su_name_{tid}", trip["name"])
    st.session_state.setdefault(f"su_ccy_{tid}", trip["home_currency"])
    st.session_state.setdefault(
        f"su_budget_{tid}", float(trip["budget_cap"]) if trip["budget_cap"] is not None else None
    )

    top, exit_col = st.columns([4, 1])
    top.subheader(f"Editing: {trip['name']}")
    if exit_col.button("Exit", key="exit_setup"):
        _save_setup_details(trip)  # persist valid details; leave regardless
        _reset_plan_ui()
        st.session_state.active_trip_id = None
        st.rerun()

    st.text_input("Trip name", key=f"su_name_{tid}")
    c1, c2 = st.columns(2)
    c1.selectbox("Home currency", CURRENCIES, key=f"su_ccy_{tid}")
    c2.number_input(
        "Flight + hotel budget",
        min_value=0.0,
        step=100.0,
        placeholder="e.g. 2000",
        key=f"su_budget_{tid}",
    )

    st.subheader("Destinations")
    for leg in trip["legs"]:
        with st.container(border=True):
            _destination_card(trip, leg)

    if st.session_state.get(f"su_adding_{tid}"):
        with st.container(border=True):
            st.markdown("**Add destination**")
            _leg_field_widgets("suadd_")
            for e in st.session_state.get("suadd_err", []):
                st.warning(e)
            b1, b2 = st.columns(2)
            if b1.button("Save destination", type="primary", key="suadd_save"):
                newleg = _draftleg_from("suadd_")
                others = [_draftleg_from_row(o) for o in trip["legs"]]
                problems = validate_new_trip("_", [newleg])
                if any(dates_overlap(newleg, o) for o in others):
                    problems.append("Dates overlap with another destination.")
                if problems:
                    st.session_state["suadd_err"] = problems
                else:
                    add_leg(tid, newleg)
                    st.session_state[f"su_adding_{tid}"] = False
                    st.session_state["suadd_err"] = []
                st.rerun()
            if b2.button("Cancel", key="suadd_cancel"):
                st.session_state[f"su_adding_{tid}"] = False
                st.session_state["suadd_err"] = []
                st.rerun()
    elif st.button("➕ Add destination", key="su_addbtn"):
        for k, v in _leg_field_defaults("suadd_").items():
            st.session_state[k] = v
        st.session_state[f"su_adding_{tid}"] = True
        st.rerun()

    for err in st.session_state.get("su_errors", []):
        st.error(err)
    if st.button("▶ Start planning", type="primary", key="su_start"):
        if trip["legs"] and _save_setup_details(trip):
            st.session_state.plan_phase = "steps"
            st.rerun()
        elif not trip["legs"]:
            st.session_state["su_errors"] = ["Add at least one destination."]
            st.rerun()


# --- guided planning steps for a draft ---------------------------------------


def _leg_span(leg: dict) -> str:
    return f"{leg['start_date'] or '?'} → {leg['end_date'] or '?'}"


def _leg_ref(leg: dict, items: list[dict]) -> tuple[float, float] | None:
    """Distance reference for a stop: the located hotel if there is one, else the
    destination anchor (PRD §6/§8). None when neither is located."""
    hotel = next(
        (
            it
            for it in items
            if it["leg_id"] == leg["id"] and it["category"] == "hotel" and it.get("lat") is not None
        ),
        None,
    )
    if hotel:
        return (float(hotel["lat"]), float(hotel["lon"]))
    if leg.get("anchor_lat") is not None:
        return (float(leg["anchor_lat"]), float(leg["anchor_lon"]))
    return None


def _item_distance(
    it: dict, spots_ll: list[tuple[float, float]], ref: tuple[float, float] | None
) -> float | None:
    """Kilometres from an item to what it's grouped around: a restaurant to its
    nearest activity (else the hotel/anchor), an activity to the hotel/anchor."""
    if it.get("lat") is None:
        return None
    p = (float(it["lat"]), float(it["lon"]))
    targets = spots_ll if it["category"] == "restaurant" and spots_ll else ([ref] if ref else [])
    return min((haversine(p, t) for t in targets), default=None)


def _move_item_cb(it: dict, home: str, sel_key: str) -> None:
    update_item(it["id"], it["cost"], it["currency"] or home, st.session_state[sel_key])


def _day_item_row(
    it: dict,
    spots_ll: list[tuple[float, float]],
    ref: tuple[float, float] | None,
    day_options: list[date | None],
    home: str,
) -> None:
    row, mv = st.columns([4, 2])
    icon = CATEGORY_ICON.get(it["category"], "")
    dist = _item_distance(it, spots_ll, ref)
    km = f" · {dist:.1f} km" if dist is not None else ""
    row.write(f"{icon} **{it['name']}**{km}")
    if it.get("address"):
        row.caption(it["address"])
    current = it.get("on_date")
    options: list[date | None] = day_options if current in day_options else [current, *day_options]

    def _label(dt: date | None) -> str:
        return f"Day {day_options.index(dt) + 1} · {dt}" if dt in day_options else "Unscheduled"

    mv.selectbox(
        "Move to",
        options,
        index=options.index(current),
        format_func=_label,
        key=f"moveday_{it['id']}",
        on_change=_move_item_cb,
        args=(it, home, f"moveday_{it['id']}"),
        label_visibility="collapsed",
    )


def _auto_arrange(
    leg: dict,
    leg_items: list[dict],
    num_days: int,
    ref: tuple[float, float] | None,
    start: date | None,
) -> None:
    """Fill undated located items into days and group them by distance (activities
    anchor the days; restaurants join their nearest activity), writing each item's
    date + within-day order. Unlocated items are left untouched (PRD §6/§8)."""
    activities = [
        (
            it["id"],
            float(it["lat"]),
            float(it["lon"]),
            (it["on_date"] - start).days if it.get("on_date") and start else None,
        )
        for it in leg_items
        if it["category"] == "spot" and it.get("lat") is not None
    ]
    restaurants = [
        (it["id"], float(it["lat"]), float(it["lon"]))
        for it in leg_items
        if it["category"] == "restaurant" and it.get("lat") is not None
    ]
    plan = plan_days(activities, restaurants, num_days, ref)
    schedule = [
        (iid, (start + timedelta(days=d) if start else None), pos)
        for d, bucket in enumerate(plan)
        for pos, (iid, _dist) in enumerate(bucket)
    ]
    reorder_items(schedule)


def _day_plan_section(trip: dict) -> None:
    """Per stop: the day-by-day schedule — activities anchor each day, restaurants
    grouped by nearest activity with distance + address, each movable to another
    day. 'Auto-arrange by distance' fills undated items in and regroups (PRD §6/§8/§9)."""
    home = trip["home_currency"]
    items = list_items(trip["id"])
    shown = False
    for leg in trip["legs"]:
        leg_items = [
            it
            for it in items
            if it["leg_id"] == leg["id"] and it["category"] in ("spot", "restaurant")
        ]
        if not leg_items:
            continue
        if not shown:
            st.markdown("**🗺 Day plan**")
            shown = True
        start, end = leg["start_date"], leg["end_date"]
        num_days = (end - start).days + 1 if start and end else 1
        ref = _leg_ref(leg, items)
        spots_ll = [
            (float(it["lat"]), float(it["lon"]))
            for it in leg_items
            if it["category"] == "spot" and it.get("lat") is not None
        ]
        day_options: list[date | None] = [
            start + timedelta(days=d) if start else None for d in range(num_days)
        ]
        st.caption(leg["city"])
        if st.button(f"🗺 Auto-arrange by distance — {leg['city']}", key=f"arrange_{leg['id']}"):
            _auto_arrange(leg, leg_items, num_days, ref, start)
            st.rerun()
        for d, date_d in enumerate(day_options):
            bucket = [it for it in leg_items if it.get("on_date") == date_d]
            label = f"Day {d + 1}" + (f" · {date_d}" if date_d else "")
            with st.expander(label, expanded=bool(bucket)):
                if not bucket:
                    st.caption("No plans yet — move an item here, or auto-arrange.")
                for it in bucket:
                    _day_item_row(it, spots_ll, ref, day_options, home)
        unscheduled = [it for it in leg_items if it.get("on_date") not in day_options]
        if unscheduled:
            with st.expander("Unscheduled", expanded=True):
                for it in unscheduled:
                    _day_item_row(it, spots_ll, ref, day_options, home)


def _render_review(trip: dict) -> None:
    tid = trip["id"]
    home = trip["home_currency"]
    st.subheader("📋 Review & finalize")
    _budget_summary(trip, home)
    _legs_summary(trip["legs"])
    _item_manager(trip, show_add=False, tag="rev")
    _day_plan_section(trip)
    st.divider()
    keep, sd, fin = st.columns([1.2, 1, 1])
    if keep.button("◀ Keep editing", key="rev_back"):
        st.session_state["plan_review"] = False
        st.rerun()
    if sd.button("💾 Save as draft", key="save_draft"):
        set_trip_status(tid, "draft")
        _reset_plan_ui()
        st.session_state.active_trip_id = None
        st.session_state.plan_msg = f"Saved '{trip['name']}' as a draft."
        st.rerun()
    if fin.button("✅ Finalize", type="primary", key="finalize"):
        set_trip_status(tid, "final")
        _reset_plan_ui()
        st.session_state.active_trip_id = None
        st.session_state.plan_msg = f"Finalized '{trip['name']}' — see the Receipts tab."
        st.rerun()


def _render_steps(trip: dict) -> None:
    legs = trip["legs"]
    home = trip["home_currency"]
    items = list_items(trip["id"])

    top, back_col, exit_col = st.columns([3, 1, 1])
    top.subheader(f"Planning: {trip['name']}")
    if back_col.button("◀ Setup", key="back_setup"):
        _reset_plan_ui()
        st.session_state.plan_phase = "setup"
        st.rerun()
    if exit_col.button("Exit", key="exit_planning"):
        _reset_plan_ui()
        st.session_state.active_trip_id = None
        st.rerun()

    if st.session_state.get("plan_review"):
        _render_review(trip)
        return

    # Plan city by city; within a city, step Flight → Hotel → Activities → Food.
    ids = [leg["id"] for leg in legs]
    if st.session_state.get("plan_dest") not in ids:
        st.session_state["plan_dest"] = ids[0]
    st.session_state.setdefault("plan_step", 0)

    def _reset_step() -> None:
        st.session_state["plan_step"] = 0

    st.radio(
        "City",
        ids,
        horizontal=True,
        format_func=lambda lid: next(
            f"{leg_['city']} · {_leg_span(leg_)}" for leg_ in legs if leg_["id"] == lid
        ),
        key="plan_dest",
        on_change=_reset_step,
        label_visibility="collapsed",
    )
    leg = next(leg_ for leg_ in legs if leg_["id"] == st.session_state["plan_dest"])
    i = ids.index(leg["id"])
    steps = _leg_steps(leg)  # Flight?/Hotel? + Activities + Food
    step = min(st.session_state["plan_step"], len(steps) - 1)

    _city_budget_bar(trip, leg, items, home)  # flight+hotel budget + extras, on top
    _anchor_row(leg)  # search anchor for the Hotel/Activities/Food steps

    def _go_next() -> None:
        idx = ids.index(st.session_state["plan_dest"])
        n = len(_leg_steps(legs[idx]))
        if st.session_state["plan_step"] < n - 1:
            st.session_state["plan_step"] += 1
        elif idx < len(ids) - 1:
            st.session_state["plan_dest"] = ids[idx + 1]
            st.session_state["plan_step"] = 0
        else:
            st.session_state["plan_review"] = True

    def _go_back() -> None:
        idx = ids.index(st.session_state["plan_dest"])
        if st.session_state["plan_step"] > 0:
            st.session_state["plan_step"] -= 1
        elif idx > 0:
            st.session_state["plan_dest"] = ids[idx - 1]
            st.session_state["plan_step"] = len(_leg_steps(legs[idx - 1])) - 1

    cat = steps[step]
    st.caption(f"Step {step + 1} of {len(steps)} · {leg['city']} · {_leg_span(leg)}")
    st.subheader(STEP_TITLE[cat])
    if cat == "flight":
        _cap_input(trip, leg, "flight_cap")
    elif cat == "hotel":
        _cap_input(trip, leg, "hotel_cap")
    else:
        st.caption("Extra — added on top of the flight+hotel budget, not capped.")

    _item_manager(
        trip, show_add=True, categories=[cat], tag=f"s{cat}d{leg['id']}", fixed_leg_id=leg["id"]
    )

    st.divider()
    bcol, ncol = st.columns(2)
    bcol.button("← Back", key="wiz_back", on_click=_go_back, disabled=(step == 0 and i == 0))
    last_step = step == len(steps) - 1
    if last_step and i == len(ids) - 1:
        nlabel = "Review trip →"
    elif last_step:
        nlabel = f"Next city: {legs[i + 1]['city']} →"
    else:
        nlabel = "Next →"
    ncol.button(nlabel, key="wiz_next", type="primary", on_click=_go_next)


# --- skeleton builder (new trip) ---------------------------------------------


def _render_skeleton() -> None:
    st.header("Plan a trip")

    st.session_state.setdefault("draft_legs", [])
    st.session_state.setdefault("adding", False)
    st.session_state.setdefault("editing_index", None)
    st.session_state.setdefault("add_errors", [])
    st.session_state.setdefault("edit_errors", [])
    st.session_state.setdefault("save_errors", [])

    st.text_input("Trip name", key="trip_name")
    c1, c2 = st.columns(2)
    home_currency = c1.selectbox("Home currency", CURRENCIES, key="trip_currency")
    budget_cap = c2.number_input(
        "Flight + hotel budget",
        min_value=0.0,
        step=100.0,
        value=None,
        placeholder="e.g. 2000",
        key="trip_budget",
    )

    st.subheader("Destinations")
    draft_legs = st.session_state.draft_legs

    for _prefix in ("a_", "e_"):
        for _k, _v in _leg_field_defaults(_prefix).items():
            st.session_state.setdefault(_k, _v)

    def _leg_problems(leg: DraftLeg, skip_index: int | None) -> list[str]:
        problems = validate_new_trip("_", [leg])  # name placeholder; check this leg only
        others = [o for k, o in enumerate(draft_legs) if k != skip_index]
        if any(dates_overlap(leg, o) for o in others):
            problems.append("Dates overlap with another destination.")
        return problems

    def _open_add() -> None:
        for k, v in _leg_field_defaults("a_").items():
            st.session_state[k] = v
        if draft_legs:  # autofill From from where the previous leg leaves you
            city, country = leg_endpoint(draft_legs[-1])
            st.session_state.a_from_city = city
            st.session_state.a_from_country = country
            if draft_legs[-1].end_date:
                st.session_state.a_start = draft_legs[-1].end_date
                st.session_state.a_end = draft_legs[-1].end_date + timedelta(days=1)
        st.session_state.adding = True
        st.session_state.add_errors = []

    def _cancel_add() -> None:
        st.session_state.adding = False
        st.session_state.add_errors = []

    def _submit_add() -> None:
        leg = _draftleg_from("a_")
        problems = _leg_problems(leg, None)
        if problems:
            st.session_state.add_errors = problems
            return
        draft_legs.append(leg)
        st.session_state.adding = False
        st.session_state.add_errors = []

    def _open_edit(i: int) -> None:
        st.session_state.editing_index = i
        st.session_state.edit_errors = []
        _seed_leg_fields("e_", draft_legs[i])

    def _cancel_edit() -> None:
        st.session_state.editing_index = None
        st.session_state.edit_errors = []

    def _submit_edit() -> None:
        idx = st.session_state.editing_index
        leg = _draftleg_from("e_")
        problems = _leg_problems(leg, idx)
        if problems:
            st.session_state.edit_errors = problems
            return
        draft_legs[idx] = leg
        st.session_state.editing_index = None
        st.session_state.edit_errors = []

    def _delete_card(i: int) -> None:
        draft_legs.pop(i)
        ei = st.session_state.editing_index
        if ei == i:
            st.session_state.editing_index = None
        elif ei is not None and ei > i:
            st.session_state.editing_index = ei - 1

    def _save_trip() -> None:
        cap = Decimal(str(st.session_state.trip_budget)) if st.session_state.trip_budget else None
        errors = validate_new_trip(st.session_state.trip_name, draft_legs)
        errors += validate_budget_caps(cap, draft_legs)
        if cap is None:
            errors.append("Set a flight + hotel budget for the trip.")
        if errors:
            st.session_state.save_errors = errors
            return
        name = st.session_state.trip_name.strip()
        tid = create_trip(name, st.session_state.trip_currency, cap, draft_legs)
        st.session_state.save_errors = []
        st.session_state.draft_legs = []
        st.session_state.adding = False
        st.session_state.editing_index = None
        st.session_state.pop("trip_name", None)  # reset the builder for the next trip
        st.session_state.pop("trip_budget", None)
        st.session_state.plan_phase = "steps"  # skeleton already set name/budget/legs
        st.session_state.active_trip_id = tid  # drop into per-destination planning
        st.session_state.plan_msg = f"Draft '{name}' created — plan each destination below."

    def _card_form(prefix: str, submit_label: str, on_submit, on_cancel, errors_key: str) -> None:
        _leg_field_widgets(prefix)
        bc1, bc2 = st.columns([1, 1])
        bc1.button(submit_label, type="primary", on_click=on_submit)
        bc2.button("Cancel", on_click=on_cancel)
        for problem in st.session_state[errors_key]:
            st.warning(problem)

    overall_cap = Decimal(str(budget_cap)) if budget_cap else None
    leg_budgets = destination_budgets(overall_cap, draft_legs)
    if st.session_state.editing_index is not None and st.session_state.editing_index >= len(
        draft_legs
    ):
        st.session_state.editing_index = None

    for i, leg in enumerate(draft_legs):
        with st.container(border=True):
            if st.session_state.editing_index == i:
                st.markdown("**Edit destination**")
                _card_form("e_", "Save changes", _submit_edit, _cancel_edit, "edit_errors")
                continue
            arrow = "⇄" if leg.round_trip else "→"
            origin = f"{leg.from_city} {arrow} " if leg.from_city else ""
            place = f"{origin}**{leg.city}**" + (f", {leg.country}" if leg.country else "")
            st.markdown(place)
            kind = "Round trip" if leg.round_trip else "One-way"
            st.caption(f"{leg.start_date} → {leg.end_date} · {kind}")
            bits: list[str] = []
            if leg.need_flight:
                bits.append("✈️ flight")
            if leg.need_hotel:
                bits.append("🏨 hotel")
            if leg.budget_cap is not None:
                bits.append(f"cap {leg.budget_cap} {home_currency}")
            budget = leg_budgets[i]
            if budget is not None:
                local_ccy = currency_for_country(leg.country, home_currency)
                if local_ccy != home_currency:
                    conv = convert(budget, home_currency, local_ccy, rates=_rates())
                    bits.append(f"≈ {conv:,.0f} {local_ccy}")
                else:
                    bits.append(f"{budget:,.0f} {home_currency}")
            if bits:
                st.caption(" · ".join(bits))
            ec1, ec2 = st.columns(2)
            ec1.button("✏️ Edit", key=f"edit_{i}", on_click=_open_edit, args=(i,))
            if ec2.button("🗑 Delete", key=f"del_{i}"):
                _delete_card(i)
                st.rerun()

    if st.session_state.adding:
        with st.container(border=True):
            st.markdown("**Add destination**")
            _card_form("a_", "Save destination", _submit_add, _cancel_add, "add_errors")
    else:
        st.button("➕ Add destination", on_click=_open_add)

    st.button("Start planning", type="primary", on_click=_save_trip)
    for err in st.session_state.save_errors:
        st.error(err)


# --- tabs --------------------------------------------------------------------

with plan_tab:
    if st.session_state.get("plan_msg"):
        st.success(st.session_state.plan_msg)
        st.session_state.plan_msg = ""
    active_id = st.session_state.get("active_trip_id")
    active_trip = next((t for t in trips if t["id"] == active_id), None) if active_id else None
    if active_id and active_trip is None:  # `trips` predates a just-saved draft; re-fetch
        active_trip = next((t for t in list_trips() if t["id"] == active_id), None)

    if active_trip is not None:
        if st.session_state.get("plan_phase", "setup") == "setup":
            _render_trip_setup(active_trip)
        else:
            _render_steps(active_trip)
    else:
        st.session_state.active_trip_id = None
        _render_skeleton()

        st.divider()
        st.subheader("Drafts")
        drafts = [t for t in trips if t.get("status") == "draft"]
        if not drafts:
            st.caption("No drafts yet.")
        for trip in drafts:
            cities = ", ".join(leg["city"] for leg in trip["legs"]) or "no cities"
            with st.expander(f"{trip['name']} · {cities}"):
                _legs_summary(trip["legs"])
                if st.button("✏️ Edit", key=f"editdraft_{trip['id']}"):
                    _reset_plan_ui()
                    st.session_state.plan_phase = "setup"
                    st.session_state.active_trip_id = trip["id"]
                    st.rerun()
                _delete_trip_control(trip)

        st.divider()
        st.subheader("Edit a finalized trip")
        finals = [t for t in trips if t.get("status") != "draft"]
        if finals:
            labels = {t["id"]: t["name"] for t in finals}
            pick = st.selectbox(
                "Trip", [t["id"] for t in finals], format_func=lambda i: labels[i], key="edit_final"
            )
            if st.button("✏️ Edit this trip", key="edit_final_go"):
                set_trip_status(pick, "draft")
                _reset_plan_ui()
                st.session_state.plan_phase = "setup"
                st.session_state.active_trip_id = pick
                st.rerun()
        else:
            st.caption("No finalized trips yet.")

with receipts_tab:
    st.header("Receipts")
    if trips:
        st.download_button(
            "⬇️ Export all trips (JSON)",
            data=export_json(trips, {t["id"]: list_items(t["id"]) for t in trips}),
            file_name="lets-go-trips.json",
            mime="application/json",
        )
    finals = [t for t in trips if t.get("status") != "draft"]
    if not finals:
        st.info("No finalized trips yet. Plan one in the Plan tab and finalize it.")
    for trip in finals:
        legs = trip["legs"]
        cities = ", ".join(leg["city"] for leg in legs) or "no cities"
        start, end = _range_bounds(legs)
        span = f"{start} – {end}" if start else "dates TBD"
        with st.expander(f"{trip['name']} · {cities} · {span}"):
            _render_receipt(trip)
            _delete_trip_control(trip)

with restaurants_tab:
    st.header("Restaurants by city")
    st.caption("Rated restaurants and wishlist, by country and city. (Phase 3.)")
