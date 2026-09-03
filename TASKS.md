# TASKS — "let's go" travel planner

Task breakdown derived from `PRD.md`, organized by phase (build order). Each phase
is shippable on its own. Check items off as completed. Per `AGENT.md`: don't
assume — confirm the "confirm at build" items when reached.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done

---

## Phase 0 — Foundations & setup

Goal: an empty but deployed, logged-in Streamlit app connected to Neon.

- [x] Create Python project scaffold (`app.py`, `requirements.txt`, `.gitignore`).
- [x] Streamlit skeleton with the **three tabs**: Plan / Receipts / Restaurants
      by city (empty placeholders).
- [x] **Neon** account + database; store connection string in Streamlit
      **secrets** (never in code).
- [x] DB connection helper + a quick "SELECT 1" health check.
- [x] **Password login** gate (Streamlit secret password; blocks all tabs until
      entered).
- [x] Secrets scaffold for future API keys (flights/hotel/currency) — empty but
      wired (`.streamlit/secrets.toml.example`).
- [x] Deploy to **Streamlit Community Cloud** (live & working). _Add to Home
      Screen on phone: optional, anytime._

## Phase 1 — Core planning (manual entry, budget, save)

Goal: build, edit, and save a trip with a working budget — no external APIs yet.

- [x] **DB schema:** `trips`, `legs` (city + date range), `items`
      (flight/hotel/spot/restaurant + cost + day + order), plus fields for
      currency and status. (Draft in PRD §7 — finalize here.)
- [x] **Create trip:** name, one or more **cities/legs** — each **From city/
      country (optional)** → **To city/country** with a **required** date range
      (end after start, no same-day) — **home currency**, single **budget cap**
      (PRD §6).
- [x] Toggle per leg: **need flight? need hotel?**
- [x] **Add item manually** (flight/hotel/spot/restaurant) with a typed cost;
      assign to a **day** (and city/leg).
- [ ] **Currency:** every cost stored + shown converted to the **home currency**
      (static/placeholder rate for now; live source in Phase 2).
- [x] **Running budget** vs cap, with a visible total/remaining indicator;
      restaurants counted as **estimates**.
- [ ] **Plan tab editing:** move item **up/down**, **change day**, and **edit
      price inline** (buttons/dropdowns — not drag-drop, PRD §9a/decisions).
- [x] **Save trip** into the collection.
- [x] **Receipts tab:** list saved trips (date range + place); **click opens the
      full plan** _(shows legs; item-level detail arrives with Add-item)_.
- [ ] **Export to file** (backup of trips + items) — PRD §5.

## Phase 2 — Auto-search & maps (the risky, defensive layer)

Goal: layer real recommendations + distance on top of the working core. Every
auto-value must remain **user-editable**; manual entry always works.

- [ ] **Currency conversion:** wire a free rate source (choose at build, PRD §10).
- [ ] **Geocoding:** locate spots/restaurants by name via **OpenStreetMap**
      (respect ~1 req/sec + user-agent).
- [ ] **Distance ordering:** order each day's items by distance (PRD §6/§8).
- [ ] **Flight auto-search:** Travelpayouts Data API (§11) — token in secrets;
      **cache results**; show cheapest within budget.
- [ ] **Hotel auto-search:** one small-quota free API (pick at build) — **cache**;
      **manual fallback** when quota/errors hit.
- [ ] **Results display:** **preferred/"liked before" on top with a mark**, then
      **cheapest-first within budget**; **"show all" (over-budget) is lazy** —
      only searched/expanded on click (PRD §6, conserves quota).
- [ ] Graceful empty/error states everywhere a free tier can fail.

## Phase 3 — Ratings, memory & wishlist

Goal: the "remember what I liked" value.

- [ ] **Rate restaurant** good / ok / bad from an opened **Receipt**, with
      optional comment.
- [ ] **Multiple dated reviews** per restaurant (by **trip date**); current
      rating = **latest** review (PRD §6/§9a).
- [ ] **Restaurants-by-city tab:** select **country → city**; filters **good / ok
      / bad / wishlist**; **expandable reviews newest → oldest**.
- [ ] **Wishlist** ("want to try") in the same tab but a **separate** filter.
- [ ] **Preferred hotels:** mark preferred → **resurface in recommendations** for
      the same area with a **"liked before"** mark.
- [ ] **Per-city average meal cost** as the primary restaurant estimate,
      **clearly marked "per-city average"**, user-overridable (PRD §6/§11).

## Phase 4 — Polish & release

- [ ] Mobile layout pass (readable/tappable on phone; test the three tabs).
- [ ] Final deploy + secrets check; confirm login + Add-to-Home-Screen flow.
- [ ] Short usage note: how to add API keys, how export/restore works.

---

## Confirm-at-build items (from PRD §10)

- [ ] Exact **hotel** API choice (small free-quota option).
- [ ] Free source for **per-city average meal cost**.
- [ ] Free source for **currency conversion** rates.

_Last updated: 2026-09-03_
