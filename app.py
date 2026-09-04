"""let's go — travel budget & planning app."""

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
    set_trip_status,
    update_item,
    update_leg,
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
CATEGORY_ICON = {"flight": "✈️", "hotel": "🏨", "spot": "📍", "restaurant": "🍽️"}
CATEGORY_LABEL = {
    "spot": "Activity",
    "flight": "Flight",
    "hotel": "Hotel",
    "restaurant": "Restaurant",
}
ALL_CATEGORIES = ["spot", "flight", "hotel", "restaurant"]
STEPS = ["Activities", "Flight & hotel", "Restaurants", "Review"]
STEP_CATEGORIES = {
    "Activities": ["spot"],
    "Flight & hotel": ["flight", "hotel"],
    "Restaurants": ["restaurant"],
}

plan_tab, receipts_tab, restaurants_tab = st.tabs(["Plan", "Receipts", "Restaurants by city"])

trips = list_trips()


def _range_bounds(legs: list[dict]) -> tuple[object, object]:
    starts = [leg["start_date"] for leg in legs if leg["start_date"]]
    ends = [leg["end_date"] for leg in legs if leg["end_date"]]
    return (min(starts) if starts else None, max(ends) if ends else None)


def _home_amount(item: dict, home: str) -> Decimal:
    return convert(item["cost"], item["currency"] or home, home)


# --- items (shared by the guided steps and the finalized receipt) ------------


def _submit_item_cb(tid: int, categories: list[str], kp: str) -> None:
    g = st.session_state
    name = g[kp + "name"]
    cost = g[kp + "cost"]
    category = categories[0] if len(categories) == 1 else g[kp + "type"]
    errors = ["Enter a cost."] if cost is None else validate_new_item(name, cost)
    if errors:
        g[kp + "err"] = errors
        return
    add_item(
        tid,
        g[kp + "leg"],
        category,
        name,
        Decimal(str(cost)),
        g[kp + "ccy"],
        int(g[kp + "day"]) or None,
    )
    g[kp + "err"] = []
    g[kp + "name"] = ""
    g[kp + "cost"] = None
    g[kp + "day"] = 0


def _item_row(it: dict, home: str, leg_label: dict) -> None:
    row, edit, remove = st.columns([6, 1, 1])
    icon = CATEGORY_ICON.get(it["category"], "")
    where = leg_label.get(it["leg_id"], "General")
    day = f" · day {it['day']}" if it["day"] else ""
    est = " (est.)" if it["category"] == "restaurant" else ""
    ccy = it["currency"] or home
    converted = f" ≈ {_home_amount(it, home)} {home}" if ccy != home else ""
    row.write(f"{icon} **{it['name']}** — {it['cost']} {ccy}{converted}{est} · {where}{day}")
    with edit.popover("✏️"):
        new_cost = st.number_input(
            "Cost", value=float(it["cost"]), min_value=0.0, step=10.0, key=f"icost_{it['id']}"
        )
        new_ccy = st.selectbox(
            "Currency",
            CURRENCIES,
            index=CURRENCIES.index(ccy) if ccy in CURRENCIES else 0,
            key=f"iccy_{it['id']}",
        )
        new_day = st.number_input(
            "Day (0 = none)", value=int(it["day"] or 0), min_value=0, step=1, key=f"iday_{it['id']}"
        )
        if st.button("Save", key=f"isave_{it['id']}"):
            update_item(it["id"], Decimal(str(new_cost)), new_ccy, int(new_day) or None)
            st.rerun()
    if remove.button("✕", key=f"rm_item_{it['id']}"):
        delete_item(it["id"])
        st.rerun()


def _item_manager(trip: dict, categories: list[str], show_add: bool, tag: str) -> None:
    tid = trip["id"]
    legs = trip["legs"]
    home = trip["home_currency"]
    leg_label = {leg["id"]: leg["city"] for leg in legs}
    items = [it for it in list_items(tid) if it["category"] in categories]

    if items:
        for it in items:
            _item_row(it, home, leg_label)
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
        "Cost", min_value=0.0, step=10.0, placeholder="e.g. 40", key=kp + "cost"
    )
    item_ccy = pc2.selectbox(
        "Currency",
        CURRENCIES,
        index=CURRENCIES.index(home) if home in CURRENCIES else 0,
        key=kp + "ccy",
    )
    if item_cost and item_ccy != home:
        st.caption(f"≈ {convert(Decimal(str(item_cost)), item_ccy, home)} {home}")
    if len(categories) > 1:
        st.selectbox("Type", categories, format_func=lambda c: CATEGORY_LABEL[c], key=kp + "type")
    st.text_input("Name", key=kp + "name")
    lc1, lc2 = st.columns(2)
    leg_choices: list[int | None] = [leg["id"] for leg in legs] + [None]
    lc1.selectbox(
        "City", leg_choices, format_func=lambda lid: leg_label.get(lid, "General"), key=kp + "leg"
    )
    lc2.number_input("Day (optional)", min_value=0, step=1, key=kp + "day")
    st.button("Add", key=kp + "btn", on_click=_submit_item_cb, args=(tid, categories, kp))
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


def _budget_bar(trip: dict, spent: float) -> None:
    home = trip["home_currency"]
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


def _render_receipt(trip: dict) -> None:
    home = trip["home_currency"]
    _legs_summary(trip["legs"])
    spent = total_spent([float(_home_amount(it, home)) for it in list_items(trip["id"])])
    _budget_bar(trip, spent)
    with st.expander("🗺 Destinations — edit or delete"):
        _destinations_editor(trip)
    _item_manager(trip, ALL_CATEGORIES, show_add=True, tag="rcpt")


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


def _leg_field_widgets(prefix: str) -> None:
    oc1, oc2 = st.columns(2)
    oc1.text_input("From city (optional)", key=f"{prefix}from_city")
    oc2.text_input("From country (optional)", key=f"{prefix}from_country")
    tc1, tc2 = st.columns(2)
    tc1.text_input("To city", key=f"{prefix}city")
    tc2.text_input("Country (optional)", key=f"{prefix}country")
    st.checkbox("Round trip (return to the From city)", key=f"{prefix}round")
    dc1, dc2 = st.columns(2)
    dc1.date_input("Start date", key=f"{prefix}start")
    dc2.date_input("End date", key=f"{prefix}end")
    st.number_input(
        "Budget cap for this stop (optional)",
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


def _destinations_editor(trip: dict) -> None:
    legs = trip["legs"]
    for leg in legs:
        lid = leg["id"]
        prefix = f"leg{lid}_"
        edit_key = f"editleg_{lid}"
        del_key = f"delleg_{lid}"
        with st.container(border=True):
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
                continue
            arrow = "⇄" if leg.get("round_trip") else "→"
            origin = f"{leg['from_city']} {arrow} " if leg.get("from_city") else ""
            place = f"{origin}**{leg['city']}**" + (f", {leg['country']}" if leg["country"] else "")
            st.markdown(place)
            st.caption(f"{leg['start_date'] or '?'} → {leg['end_date'] or '?'}")
            c1, c2 = st.columns(2)
            if c1.button("✏️ Edit", key=f"edleg_{lid}"):
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
            elif c2.button("🗑 Delete", key=f"delbtn_{lid}"):
                st.session_state[del_key] = True
                st.rerun()


# --- guided planning steps for a draft ---------------------------------------


def _render_steps(trip: dict) -> None:
    tid = trip["id"]
    top, exit_col = st.columns([4, 1])
    top.subheader(f"Planning: {trip['name']}")
    if exit_col.button("Exit", key="exit_planning"):
        st.session_state.active_trip_id = None
        st.rerun()
    st.caption("Draft — build it up step by step, then generate the receipt.")

    home = trip["home_currency"]
    _budget_bar(trip, total_spent([float(_home_amount(it, home)) for it in list_items(tid)]))

    with st.expander("🗺 Destinations — edit or delete"):
        _destinations_editor(trip)

    st.session_state.setdefault("plan_step", STEPS[0])
    step = st.radio("Step", STEPS, horizontal=True, key="plan_step", label_visibility="collapsed")
    st.divider()

    if step == "Review":
        _legs_summary(trip["legs"])
        _item_manager(trip, ALL_CATEGORIES, show_add=False, tag="rev")
        if st.button("✅ Generate receipt", type="primary", key="gen_receipt"):
            set_trip_status(tid, "final")
            st.session_state.active_trip_id = None
            st.session_state.plan_msg = (
                f"Receipt for '{trip['name']}' finalized — see the Receipts tab."
            )
            st.rerun()
    else:
        _item_manager(trip, STEP_CATEGORIES[step], show_add=True, tag=step[:4])


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
        "Budget cap",
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
            errors.append("Set a budget cap for the trip.")
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
        st.session_state.active_trip_id = tid  # drop into the guided steps
        st.session_state.plan_step = STEPS[0]
        st.session_state.plan_msg = f"Draft '{name}' created — plan it step by step."

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
                    bits.append(f"≈ {convert(budget, home_currency, local_ccy):,.0f} {local_ccy}")
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
    if active_id and active_trip is None:
        # `trips` was read at the top of the run, before a just-saved draft
        # existed; re-fetch so a new draft opens in the steps rather than falling
        # back to the skeleton (with the draft only showing in Receipts).
        active_trip = next((t for t in list_trips() if t["id"] == active_id), None)
    if active_trip is not None:
        _render_steps(active_trip)
    else:
        st.session_state.active_trip_id = None
        _render_skeleton()

with receipts_tab:
    st.header("Receipts")
    _active_id = st.session_state.get("active_trip_id")
    _active = next((t for t in trips if t["id"] == _active_id), None) if _active_id else None
    if _active is not None:
        st.info(f"▶️ You're planning **{_active['name']}** — open the **Plan** tab to continue.")
    if not trips:
        st.info("No trips yet. Create one in the Plan tab.")
    else:
        st.download_button(
            "⬇️ Export all trips (JSON)",
            data=export_json(trips, {t["id"]: list_items(t["id"]) for t in trips}),
            file_name="lets-go-trips.json",
            mime="application/json",
        )
        drafts = [t for t in trips if t.get("status") == "draft"]
        finals = [t for t in trips if t.get("status") != "draft"]

        if drafts:
            st.subheader("Drafts (in progress)")
            for trip in drafts:
                legs = trip["legs"]
                cities = ", ".join(leg["city"] for leg in legs) or "no cities"
                start, end = _range_bounds(legs)
                span = f"{start} – {end}" if start else "dates TBD"
                with st.expander(f"{trip['name']} · {cities} · {span}"):
                    _legs_summary(legs)
                    home = trip["home_currency"]
                    spent = total_spent(
                        [float(_home_amount(it, home)) for it in list_items(trip["id"])]
                    )
                    _budget_bar(trip, spent)
                    rc1, rc2 = st.columns(2)
                    if rc1.button("▶️ Resume planning", key=f"resume_{trip['id']}"):
                        st.session_state.active_trip_id = trip["id"]
                        st.rerun()
                    if rc2.button("✅ Finalize", key=f"fin_{trip['id']}"):
                        set_trip_status(trip["id"], "final")
                        st.rerun()
                    _delete_trip_control(trip)
                    st.caption("Add and reorder items in the Plan tab's steps (Resume planning).")

        if finals:
            st.subheader("Finalized")
            for trip in finals:
                legs = trip["legs"]
                cities = ", ".join(leg["city"] for leg in legs) or "no cities"
                start, end = _range_bounds(legs)
                span = f"{start} – {end}" if start else "dates TBD"
                with st.expander(f"{trip['name']} · {cities} · {span}"):
                    _delete_trip_control(trip)
                    _render_receipt(trip)

with restaurants_tab:
    st.header("Restaurants by city")
    st.caption("Rated restaurants and wishlist, by country and city. (Phase 3.)")
