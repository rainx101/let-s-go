"""let's go — travel budget & planning app. Phase 0 skeleton: login gate +
three-tab layout. Tabs are placeholders; features come in later phases."""

import streamlit as st

from lets_go.auth import require_login

st.set_page_config(page_title="let's go", page_icon="🧳", layout="centered")

require_login()

st.title("🧳 let's go")

plan_tab, receipts_tab, restaurants_tab = st.tabs(["Plan", "Receipts", "Restaurants by city"])

with plan_tab:
    st.header("Plan")
    st.caption("Build a trip: budget, flights, hotels, spots. (Coming in Phase 1.)")

with receipts_tab:
    st.header("Receipts")
    st.caption("Saved trips — open one to see the full plan and rate it. (Phase 1/3.)")

with restaurants_tab:
    st.header("Restaurants by city")
    st.caption("Rated restaurants and wishlist, by country and city. (Phase 3.)")
