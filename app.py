"""let's go — travel budget & planning app.
Phase 1 (slice 1): create and list trips."""

from datetime import date, timedelta
from decimal import Decimal

import streamlit as st

from lets_go.auth import require_login
from lets_go.budget import budget_progress, is_over_budget, remaining_budget, total_spent
from lets_go.db import health_check, init_db
from lets_go.trips import (
    DraftLeg,
    add_item,
    create_trip,
    delete_item,
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

    name = st.text_input("Trip name", key="trip_name")
    c1, c2 = st.columns(2)
    home_currency = c1.selectbox("Home currency", CURRENCIES, key="trip_currency")
    budget_cap = c2.number_input("Budget cap", min_value=0.0, step=100.0, key="trip_budget")

    st.subheader("Destinations")
    st.session_state.setdefault("editing_index", None)
    draft_legs = st.session_state.draft_legs

    for i, leg in enumerate(draft_legs):
        row, edit, remove = st.columns([6, 1, 1])
        flags = ("✈️" if leg.need_flight else "") + ("🏨" if leg.need_hotel else "")
        origin = f"{leg.from_city} → " if leg.from_city else ""
        place = f"{origin}**{leg.city}**" + (f", {leg.country}" if leg.country else "")
        cap = f" · cap {leg.budget_cap}" if leg.budget_cap is not None else ""
        row.write(f"{place} · {leg.start_date} → {leg.end_date}{cap} {flags}")
        if edit.button("✏️", key=f"ed_{i}"):
            st.session_state.editing_index = i
            st.rerun()
        if remove.button("✕", key=f"rm_{i}"):
            draft_legs.pop(i)
            st.session_state.editing_index = None
            st.rerun()

    idx = st.session_state.editing_index
    ed = draft_legs[idx] if idx is not None and idx < len(draft_legs) else None
    today = date.today()

    if ed is not None:
        st.info(f"Editing destination {idx + 1}: {ed.city or 'unnamed'}")
        if st.button("Cancel edit"):
            st.session_state.editing_index = None
            st.rerun()

    with st.form("add_city", clear_on_submit=True):
        st.markdown("**Edit destination**" if ed else "**Add destination**")
        oc1, oc2 = st.columns(2)
        from_city = oc1.text_input("From city (optional)", value=ed.from_city if ed else "")
        from_country = oc2.text_input(
            "From country (optional)", value=ed.from_country if ed else ""
        )
        tc1, tc2 = st.columns(2)
        city = tc1.text_input("To city", value=ed.city if ed else "")
        country = tc2.text_input("Country (optional)", value=ed.country if ed else "")
        dc1, dc2 = st.columns(2)
        start = dc1.date_input("Start date", value=ed.start_date if ed else today)
        end = dc2.date_input("End date", value=ed.end_date if ed else today + timedelta(days=1))
        leg_cap = st.number_input(
            "Budget cap for this stop (optional)",
            min_value=0.0,
            step=100.0,
            value=float(ed.budget_cap) if ed and ed.budget_cap else 0.0,
        )
        fc, hc = st.columns(2)
        need_flight = fc.checkbox("Need flight", value=ed.need_flight if ed else False)
        need_hotel = hc.checkbox("Need hotel", value=ed.need_hotel if ed else False)
        if st.form_submit_button("Save changes" if ed else "Add destination"):
            leg = DraftLeg(
                city=normalize_place(city),
                country=country.strip(),
                from_city=normalize_place(from_city),
                from_country=from_country.strip(),
                start_date=start,
                end_date=end,
                need_flight=need_flight,
                need_hotel=need_hotel,
                budget_cap=Decimal(str(leg_cap)) if leg_cap else None,
            )
            problems = validate_new_trip("_", [leg])  # name placeholder; check this leg only
            if problems:
                for p in problems:
                    st.warning(p)
            elif ed is not None:
                draft_legs[idx] = leg
                st.session_state.editing_index = None
                st.rerun()
            else:
                draft_legs.append(leg)
                st.rerun()

    if st.button("Save trip", type="primary"):
        cap = Decimal(str(budget_cap)) if budget_cap else None
        errors = validate_new_trip(name, draft_legs) + validate_budget_caps(cap, draft_legs)
        if errors:
            for err in errors:
                st.error(err)
        else:
            trip_id = create_trip(name, home_currency, cap, draft_legs)
            st.session_state.draft_legs = []
            st.session_state.editing_index = None
            st.success(f"Saved trip #{trip_id}. See the Receipts tab.")

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
        currency = trip["home_currency"]
        items = list_items(trip_id)

        spent = total_spent([float(it["cost"]) for it in items])
        if trip["budget_cap"] is not None:
            cap = float(trip["budget_cap"])
            st.progress(budget_progress(cap, spent))
            left = remaining_budget(cap, [spent])
            msg = f"Spent {spent:,.2f} / {cap:,.2f} {currency} · {left:,.2f} left"
            if is_over_budget(cap, [spent]):
                st.error(f"{msg} — over budget")
            else:
                st.caption(msg)
        else:
            st.caption(f"Spent {spent:,.2f} {currency} · no budget cap set")

        # leg picker options: each leg, plus "General" (no city)
        leg_choices: list[int | None] = [leg["id"] for leg in legs] + [None]
        leg_label = {leg["id"]: leg["city"] for leg in legs}

        with st.form("add_item", clear_on_submit=True):
            ic1, ic2 = st.columns(2)
            category = ic1.selectbox("Type", ITEM_CATEGORIES)
            item_cost = ic2.number_input(f"Cost ({currency})", min_value=0.0, step=10.0)
            item_name = st.text_input("Name")
            lc1, lc2 = st.columns(2)
            item_leg = lc1.selectbox(
                "City",
                leg_choices,
                format_func=lambda lid: leg_label.get(lid, "General"),
            )
            item_day = lc2.number_input("Day (optional)", min_value=0, step=1)
            if st.form_submit_button("Add item"):
                item_errors = validate_new_item(item_name, item_cost)
                if item_errors:
                    for err in item_errors:
                        st.error(err)
                else:
                    add_item(
                        trip_id,
                        item_leg,
                        category,
                        item_name,
                        Decimal(str(item_cost)),
                        item_day or None,
                    )
                    st.rerun()

        for it in items:
            row, remove = st.columns([6, 1])
            icon = CATEGORY_ICON.get(it["category"], "")
            where = leg_label.get(it["leg_id"], "General")
            day = f" · day {it['day']}" if it["day"] else ""
            est = " (est.)" if it["category"] == "restaurant" else ""
            row.write(f"{icon} **{it['name']}** — {it['cost']} {currency}{est} · {where}{day}")
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
