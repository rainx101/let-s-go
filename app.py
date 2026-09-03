"""let's go — travel budget & planning app.
Phase 1 (slice 1): create and list trips."""

from datetime import date, timedelta
from decimal import Decimal

import streamlit as st

from lets_go.auth import require_login
from lets_go.budget import budget_progress, is_over_budget, remaining_budget, total_spent
from lets_go.currency import convert, currency_for_country
from lets_go.db import health_check, init_db
from lets_go.trips import (
    DraftLeg,
    add_item,
    create_trip,
    delete_item,
    destination_budgets,
    list_items,
    list_trips,
    normalize_place,
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

CURRENCIES = ["USD", "EUR", "JPY", "GBP", "AUD", "CAD", "TWD", "KRW", "THB"]
ITEM_CATEGORIES = ["flight", "hotel", "spot", "restaurant"]
CATEGORY_ICON = {"flight": "✈️", "hotel": "🏨", "spot": "📍", "restaurant": "🍽️"}

plan_tab, receipts_tab, restaurants_tab = st.tabs(["Plan", "Receipts", "Restaurants by city"])

trips = list_trips()


def _range_bounds(legs: list[dict]) -> tuple[object, object]:
    starts = [leg["start_date"] for leg in legs if leg["start_date"]]
    ends = [leg["end_date"] for leg in legs if leg["end_date"]]
    return (min(starts) if starts else None, max(ends) if ends else None)


with plan_tab:
    st.header("Plan a trip")

    st.session_state.setdefault("draft_legs", [])

    st.text_input("Trip name", key="trip_name")
    c1, c2 = st.columns(2)
    home_currency = c1.selectbox("Home currency", CURRENCIES, key="trip_currency")
    budget_cap = c2.number_input("Budget cap", min_value=0.0, step=100.0, key="trip_budget")

    st.subheader("Destinations")
    st.session_state.setdefault("editing_index", None)
    st.session_state.setdefault("dest_errors", [])
    st.session_state.setdefault("save_errors", [])
    st.session_state.setdefault("save_success", "")
    draft_legs = st.session_state.draft_legs
    today = date.today()

    # Field state lives in session_state (keyed widgets, not a form) so Enter
    # doesn't auto-submit and Edit can reliably repopulate the fields.
    field_defaults = {
        "d_from_city": "",
        "d_from_country": "",
        "d_city": "",
        "d_country": "",
        "d_start": today,
        "d_end": today + timedelta(days=1),
        "d_cap": 0.0,
        "d_flight": False,
        "d_hotel": False,
    }
    for _k, _v in field_defaults.items():
        st.session_state.setdefault(_k, _v)

    def _reset_destination_fields() -> None:
        st.session_state.editing_index = None
        st.session_state.dest_errors = []
        for k, v in field_defaults.items():
            st.session_state[k] = v

    def _load_destination(i: int) -> None:
        leg = draft_legs[i]
        st.session_state.editing_index = i
        st.session_state.dest_errors = []
        st.session_state.d_from_city = leg.from_city
        st.session_state.d_from_country = leg.from_country
        st.session_state.d_city = leg.city
        st.session_state.d_country = leg.country
        st.session_state.d_start = leg.start_date or today
        st.session_state.d_end = leg.end_date or today + timedelta(days=1)
        st.session_state.d_cap = float(leg.budget_cap) if leg.budget_cap else 0.0
        st.session_state.d_flight = leg.need_flight
        st.session_state.d_hotel = leg.need_hotel

    def _submit_destination() -> None:
        leg = DraftLeg(
            city=normalize_place(st.session_state.d_city),
            country=st.session_state.d_country.strip(),
            from_city=normalize_place(st.session_state.d_from_city),
            from_country=st.session_state.d_from_country.strip(),
            start_date=st.session_state.d_start,
            end_date=st.session_state.d_end,
            need_flight=st.session_state.d_flight,
            need_hotel=st.session_state.d_hotel,
            budget_cap=Decimal(str(st.session_state.d_cap)) if st.session_state.d_cap else None,
        )
        problems = validate_new_trip("_", [leg])  # name placeholder; check this leg only
        if problems:
            st.session_state.dest_errors = problems
            return
        idx = st.session_state.editing_index
        if idx is not None and idx < len(draft_legs):
            draft_legs[idx] = leg
        else:
            draft_legs.append(leg)
        _reset_destination_fields()

    def _save_trip() -> None:
        cap = Decimal(str(st.session_state.trip_budget)) if st.session_state.trip_budget else None
        errors = validate_new_trip(st.session_state.trip_name, draft_legs)
        errors += validate_budget_caps(cap, draft_legs)
        if errors:
            st.session_state.save_errors = errors
            return
        trip_id = create_trip(
            st.session_state.trip_name, st.session_state.trip_currency, cap, draft_legs
        )
        st.session_state.save_errors = []
        st.session_state.save_success = f"Saved trip #{trip_id}. See the Receipts tab."
        st.session_state.draft_legs = []
        _reset_destination_fields()

    overall_cap = Decimal(str(budget_cap)) if budget_cap else None
    leg_budgets = destination_budgets(overall_cap, draft_legs)

    for i, leg in enumerate(draft_legs):
        row, edit, remove = st.columns([6, 1, 1])
        flags = ("✈️" if leg.need_flight else "") + ("🏨" if leg.need_hotel else "")
        origin = f"{leg.from_city} → " if leg.from_city else ""
        place = f"{origin}**{leg.city}**" + (f", {leg.country}" if leg.country else "")
        cap = f" · cap {leg.budget_cap}" if leg.budget_cap is not None else ""
        row.write(f"{place} · {leg.start_date} → {leg.end_date}{cap} {flags}")
        budget = leg_budgets[i]
        if budget is not None:
            local_ccy = currency_for_country(leg.country, home_currency)
            share = "" if leg.budget_cap is not None else " share of budget"
            if local_ccy != home_currency:
                local = convert(budget, home_currency, local_ccy)
                row.caption(f"≈ {local:,.0f} {local_ccy} · {budget:,.0f} {home_currency}{share}")
            else:
                row.caption(f"{budget:,.0f} {home_currency}{share}")
        edit.button("✏️", key=f"ed_{i}", on_click=_load_destination, args=(i,))
        if remove.button("✕", key=f"rm_{i}"):
            draft_legs.pop(i)
            _reset_destination_fields()
            st.rerun()

    editing = st.session_state.editing_index is not None
    st.markdown("**Edit destination**" if editing else "**Add destination**")
    oc1, oc2 = st.columns(2)
    oc1.text_input("From city (optional)", key="d_from_city")
    oc2.text_input("From country (optional)", key="d_from_country")
    tc1, tc2 = st.columns(2)
    tc1.text_input("To city", key="d_city")
    tc2.text_input("Country (optional)", key="d_country")
    dc1, dc2 = st.columns(2)
    dc1.date_input("Start date", key="d_start")
    dc2.date_input("End date", key="d_end")
    st.number_input("Budget cap for this stop (optional)", min_value=0.0, step=100.0, key="d_cap")
    fc, hc = st.columns(2)
    fc.checkbox("Need flight", key="d_flight")
    hc.checkbox("Need hotel", key="d_hotel")

    bc1, bc2 = st.columns([1, 1])
    bc1.button(
        "Save changes" if editing else "Add destination",
        type="secondary",
        on_click=_submit_destination,
    )
    if editing:
        bc2.button("Cancel edit", on_click=_reset_destination_fields)
    for problem in st.session_state.dest_errors:
        st.warning(problem)

    st.button("Save trip", type="primary", on_click=_save_trip)
    for err in st.session_state.save_errors:
        st.error(err)
    if st.session_state.save_success:
        st.success(st.session_state.save_success)
        st.session_state.save_success = ""

    st.divider()
    st.subheader("Add items to a trip")
    if not trips:
        st.caption("Save a trip above first, then add flights, hotels, spots and meals.")
    else:
        labels = {t["id"]: t["name"] for t in trips}
        trip_id = st.selectbox(
            "Trip",
            options=[t["id"] for t in trips],
            format_func=lambda tid: labels[tid],
            key="edit_trip",
        )
        trip = next(t for t in trips if t["id"] == trip_id)
        legs = trip["legs"]
        home = trip["home_currency"]
        items = list_items(trip_id)

        def home_amount(item: dict) -> Decimal:
            return convert(item["cost"], item["currency"] or home, home)

        spent = total_spent([float(home_amount(it)) for it in items])
        if trip["budget_cap"] is not None:
            cap = float(trip["budget_cap"])
            st.progress(budget_progress(cap, spent))
            left = remaining_budget(cap, [spent])
            msg = f"Spent {spent:,.2f} / {cap:,.2f} {home} · {left:,.2f} left"
            if is_over_budget(cap, [spent]):
                st.error(f"{msg} — over budget")
            else:
                st.caption(msg)
        else:
            st.caption(f"Spent {spent:,.2f} {home} · no budget cap set")

        # leg picker options: each leg, plus "General" (no city)
        leg_choices: list[int | None] = [leg["id"] for leg in legs] + [None]
        leg_label = {leg["id"]: leg["city"] for leg in legs}
        leg_key = f"new_item_leg_{trip_id}"  # per-trip so switching trips can't mismatch options
        st.session_state.setdefault("item_errors", [])

        def _submit_item(tid: int, lkey: str) -> None:
            name = st.session_state.new_item_name
            cost = st.session_state.new_item_cost
            errors = validate_new_item(name, cost)
            if errors:
                st.session_state.item_errors = errors
                return
            add_item(
                tid,
                st.session_state[lkey],
                st.session_state.new_item_type,
                name,
                Decimal(str(cost)),
                st.session_state.new_item_ccy,
                int(st.session_state.new_item_day) or None,
            )
            st.session_state.item_errors = []
            st.session_state.new_item_name = ""
            st.session_state.new_item_cost = 0.0
            st.session_state.new_item_day = 0

        # No form → Enter won't auto-submit; cost/currency preview the conversion live.
        pc1, pc2 = st.columns([3, 1])
        item_cost = pc1.number_input("Cost", min_value=0.0, step=10.0, key="new_item_cost")
        item_currency = pc2.selectbox(
            "Currency",
            CURRENCIES,
            index=CURRENCIES.index(home) if home in CURRENCIES else 0,
            key="new_item_ccy",
        )
        if item_cost and item_currency != home:
            st.caption(f"≈ {convert(Decimal(str(item_cost)), item_currency, home)} {home}")

        st.selectbox("Type", ITEM_CATEGORIES, key="new_item_type")
        st.text_input("Name", key="new_item_name")
        lc1, lc2 = st.columns(2)
        lc1.selectbox(
            "City", leg_choices, format_func=lambda lid: leg_label.get(lid, "General"), key=leg_key
        )
        lc2.number_input("Day (optional)", min_value=0, step=1, key="new_item_day")
        st.button("Add item", on_click=_submit_item, args=(trip_id, leg_key))
        for err in st.session_state.item_errors:
            st.error(err)

        for it in items:
            row, remove = st.columns([6, 1])
            icon = CATEGORY_ICON.get(it["category"], "")
            where = leg_label.get(it["leg_id"], "General")
            day = f" · day {it['day']}" if it["day"] else ""
            est = " (est.)" if it["category"] == "restaurant" else ""
            ccy = it["currency"] or home
            converted = f" ≈ {home_amount(it)} {home}" if ccy != home else ""
            price = f"{it['cost']} {ccy}{converted}"
            row.write(f"{icon} **{it['name']}** — {price}{est} · {where}{day}")
            if remove.button("✕", key=f"rm_item_{it['id']}"):
                delete_item(it["id"])
                st.rerun()

with receipts_tab:
    st.header("Receipts")
    if not trips:
        st.info("No trips yet. Create one in the Plan tab.")
    for trip in trips:
        legs = trip["legs"]
        cities = ", ".join(leg["city"] for leg in legs) or "no cities"
        start, end = _range_bounds(legs)
        span = f"{start} – {end}" if start else "dates TBD"
        with st.expander(f"{trip['name']} · {cities} · {span}"):
            if trip["budget_cap"] is not None:
                st.write(f"Budget cap: {trip['budget_cap']} {trip['home_currency']}")
            for leg in legs:
                flags = ("✈️" if leg["need_flight"] else "") + ("🏨" if leg["need_hotel"] else "")
                origin = f"{leg['from_city']} → " if leg.get("from_city") else ""
                place = f"{origin}**{leg['city']}**" + (
                    f", {leg['country']}" if leg["country"] else ""
                )
                cap = f" · cap {leg['budget_cap']}" if leg.get("budget_cap") is not None else ""
                span = f"{leg['start_date'] or '?'} → {leg['end_date'] or '?'}"
                st.write(f"- {place} · {span}{cap} {flags}")

with restaurants_tab:
    st.header("Restaurants by city")
    st.caption("Rated restaurants and wishlist, by country and city. (Phase 3.)")
