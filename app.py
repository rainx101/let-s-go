"""let's go — travel budget & planning app.
Phase 1 (slice 1): create and list trips."""

from decimal import Decimal

import streamlit as st

from lets_go.auth import require_login
from lets_go.db import health_check, init_db
from lets_go.trips import DraftLeg, create_trip, list_trips, validate_new_trip

st.set_page_config(page_title="let's go", page_icon="🧳", layout="centered")

require_login()
init_db()

st.title("🧳 let's go")

with st.sidebar:
    st.caption("Database")
    if health_check():
        st.success("Neon connected", icon="✅")

CURRENCIES = ["USD", "EUR", "JPY", "GBP", "AUD", "CAD", "TWD", "KRW", "THB"]

plan_tab, receipts_tab, restaurants_tab = st.tabs(["Plan", "Receipts", "Restaurants by city"])


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

    st.subheader("Cities")
    with st.form("add_city", clear_on_submit=True):
        city = st.text_input("City")
        country = st.text_input("Country (optional)")
        set_dates = st.checkbox("Set dates")
        start = end = None
        if set_dates:
            dc1, dc2 = st.columns(2)
            start = dc1.date_input("Start")
            end = dc2.date_input("End")
        fc, hc = st.columns(2)
        need_flight = fc.checkbox("Need flight")
        need_hotel = hc.checkbox("Need hotel")
        if st.form_submit_button("Add city"):
            if city.strip():
                st.session_state.draft_legs.append(
                    DraftLeg(city, country, start, end, need_flight, need_hotel)
                )
            else:
                st.warning("Enter a city name.")

    for i, leg in enumerate(st.session_state.draft_legs):
        row, remove = st.columns([6, 1])
        flags = ("✈️" if leg.need_flight else "") + ("🏨" if leg.need_hotel else "")
        dates = f"{leg.start_date or '?'} → {leg.end_date or '?'}"
        row.write(f"**{leg.city}** {leg.country} · {dates} {flags}")
        if remove.button("✕", key=f"rm_{i}"):
            st.session_state.draft_legs.pop(i)
            st.rerun()

    if st.button("Save trip", type="primary"):
        errors = validate_new_trip(name, st.session_state.draft_legs)
        if errors:
            for err in errors:
                st.error(err)
        else:
            cap = Decimal(str(budget_cap)) if budget_cap else None
            trip_id = create_trip(name, home_currency, cap, st.session_state.draft_legs)
            st.session_state.draft_legs = []
            st.success(f"Saved trip #{trip_id}. See the Receipts tab.")

with receipts_tab:
    st.header("Receipts")
    trips = list_trips()
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
                st.write(
                    f"- **{leg['city']}** {leg['country'] or ''} · "
                    f"{leg['start_date'] or '?'} → {leg['end_date'] or '?'} {flags}"
                )

with restaurants_tab:
    st.header("Restaurants by city")
    st.caption("Rated restaurants and wishlist, by country and city. (Phase 3.)")
