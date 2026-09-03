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

## Phase 1 — Skeleton & manual core (mostly done)

Goal: build, edit, and save a trip skeleton with a working budget — no external
APIs yet. (Reorganized 2026-09-03 to match the guided flow, PRD §9.)

- [x] **DB schema:** `trips`, `legs` (city + date range), `items`
      (flight/hotel/spot/restaurant + cost + currency + day + order + status).
- [x] **Create trip skeleton:** name, one or more **cities/legs** — each **From
      city/country (optional)** → **To city/country** with **required** Start/End
      dates (end after start, no same-day, **no overlaps**) and an **optional
      per-stop budget cap** (sum can't exceed the trip cap); **editable in place**
      before saving — **home currency**, single overall **budget cap** (PRD §6).
- [x] Toggle per leg: **need flight? need hotel?**
- [x] **Add item manually** (flight/hotel/spot/restaurant) with a typed cost +
      currency; assign to a **day** (and city/leg).
- [x] **Currency:** every cost stored (original amount + currency) + shown
      converted to the **home currency** (static/placeholder rate for now; live
      source in Phase 3).
- [x] **Running budget** vs cap, with a visible total/remaining indicator;
      restaurants counted as **estimates**.
- [x] **Trip type:** **round-trip / one-way** toggle at setup (stored on the
      trip; the return-to-origin flight segment itself is Phase 2/3). (PRD §6.)
- [x] **Trip status:** `trips.status` = **draft / final**; skeleton saves as a
      **draft**; Receipts splits Drafts (with Finalize) from Finalized (with
      Reopen). (PRD §9; Phase 2 Slice 1.)
- [x] **Item editing:** **change day** and **edit price/cost (+ currency) inline**
      (per-item popover). Manual up/down reordering lives at the **receipt / full
      plan** (Phase 2), where distance ordering (Phase 3) recommends the sequence.
- [x] **Save trip** into the collection.
- [x] **Receipts tab:** list saved trips (date range + place); **click opens the
      full plan** _(shows legs; item-level detail arrives with the guided flow)_.
- [x] **Export to file** (JSON backup of trips + legs + items) — PRD §5.

## Phase 2 — Guided flow (manual, budget-anchored)

Goal: the step-by-step pipeline (PRD §9) with the **waterfall budget** (PRD §6),
still on **manual entry** — search is layered on in Phase 3. Draft saved early,
finalized at the end.

- [ ] **Wizard steps:** Skeleton → **Activities** → **Flight & hotel** →
      **Restaurants** → **Generate receipt**, with a persistent **budget header**.
- [ ] **Activities first:** add activities (day optional), **fixed price hand-typed**
      (search in Phase 3); spent off the top of the budget.
- [ ] **Waterfall budget:** activities locked → choose a **flight+hotel** amount
      from the remainder → **restaurants get the rest**; header shows all three.
- [ ] **Draft persistence:** save the skeleton as a **draft** at setup and update
      it through the steps; **finalize** on receipt save (PRD §9).
- [ ] **Generate receipt / full plan:** recommend a **day** for undated
      activities; **move items up/down** to arrange each day.
- [ ] **Receipt editing:** swap a hotel/other pick, edit items, **hand-type the
      real amount paid** for an accurate budget; re-finalize.
- [ ] Finalized trip appears in **Receipts** (also reorderable / editable).

## Phase 3 — Auto-search & maps (the risky, defensive layer)

Goal: layer real recommendations + distance on top of the working guided flow.
Every auto-value must remain **user-editable**; manual entry always works.

- [ ] **Currency conversion:** wire a free rate source (choose at build, PRD §10).
- [ ] **Geocoding:** locate activities/restaurants by name via **OpenStreetMap**
      (respect ~1 req/sec + user-agent).
- [ ] **Distance ordering:** order each day's items by distance; **place
      restaurants near the activities** (PRD §6/§8/§9).
- [ ] **Flight auto-search:** Travelpayouts Data API (§11) — token in secrets;
      **cache results**; cheapest within the **flight+hotel** allocation.
- [ ] **Hotel auto-search:** one small-quota free API (pick at build) — **cache**;
      **manual fallback** when quota/errors hit.
- [ ] **Activity price search:** best-effort source if one exists; **hand-type
      fallback** always available (PRD §11).
- [ ] **Results display:** **preferred/"liked before" on top with a mark**, then
      **cheapest-first within the category's budget**; **"show all" (over-budget)
      is lazy** — only searched/expanded on click (PRD §6, conserves quota).
- [ ] Graceful empty/error states everywhere a free tier can fail.

## Phase 4 — Ratings, memory & wishlist

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

## Phase 5 — Polish & release

- [ ] Mobile layout pass (readable/tappable on phone; test the three tabs).
- [ ] Final deploy + secrets check; confirm login + Add-to-Home-Screen flow.
- [ ] Short usage note: how to add API keys, how export/restore works.

---

## Confirm-at-build items (from PRD §10)

- [ ] Exact **hotel** API choice (small free-quota option).
- [ ] Free source for **per-city average meal cost**.
- [ ] Free source for **currency conversion** rates.
- [ ] Any free/affordable source for **activity prices** — else hand-type stays
      the baseline (PRD §11).

_Last updated: 2026-09-03_
