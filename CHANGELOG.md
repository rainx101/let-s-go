# CHANGELOG

Progress log for "let's go". **Rule:** entries by **date + topic**, newest at the
top → oldest at the bottom. Each entry records **what we did** and the **next
step**.

---

## 2026-09-03 — Builder fixes + per-card local-currency budgets

**What we did**
- **Destination builder reliability:** replaced the `st.form` with keyed
  `session_state` widgets + callbacks. Fixes two reported bugs — pressing Enter
  in a field no longer auto-adds a destination, and **Edit (✏️) now repopulates
  the whole card** so a stop can actually be changed. Add/Save/Cancel/Remove all
  manage edit state; validation errors show while preserving what you typed.
- **Per-destination budget on each card:** shows a stop's effective budget in the
  **local currency**, inferred from the country. `destination_budgets` (pure,
  tested): a stop's own cap when set, else an even share of the overall budget
  left after the capped stops (e.g. 500 with two capless stops → 250 each);
  `currency_for_country` maps country → currency, falling back to the home
  currency when unknown.
- **Add-item: same Enter fix** — dropped its form too, so Enter in the item name
  no longer auto-adds; per-trip leg key avoids option mismatches on trip switch.
- **Clear destination fields after "Save trip"** — the builder resets to a clean
  slate for the next trip.
- **Tests:** 8 new (44 total) for `destination_budgets` and `currency_for_country`.
- Verified: ruff/ty/pytest green; live split+conversion scenario matches;
  app loads clean.

**Next step**
- Rest of Phase 1: inline item editing (move up/down, change day, edit price)
  and export to file. Then Phase 2 (search + live rates/geocoding).

## 2026-09-03 — Editable destinations + per-stop budget caps

**What we did**
- **Dates as two boxes:** Start date / End date (still required, end after start)
  instead of a single range picker.
- **Edit a drafted destination:** each stop has ✏️ (pre-fills the form to update
  it in place) and ✕; a "Cancel edit" escape hatch. Driven by an
  `editing_index` in session state.
- **Per-destination budget cap** (optional) on each stop —
  `legs.budget_cap` added idempotently (verified live). Shown in the draft list
  and Receipts.
- **Rule:** `validate_budget_caps` — the sum of per-stop caps may not exceed the
  overall trip cap (no trip cap ⇒ no constraint; capless stops ignored). Checked
  at Save alongside the leg validation.
- **Rule:** a destination can't equal its departure city (case/space-insensitive).
- **Place cleanup:** `normalize_place` trims, collapses whitespace, and Title
  Cases city names on entry (real place validation via geocoding is Phase 2).
- **Currency conversion (static rates):** new `lets_go/currency.py` with
  `convert` + a placeholder rate table (live source is Phase 2). Items now store
  their **original amount + currency**; the add-item form has a **currency
  selector with a live "≈ home" preview**, the item list shows original ≈
  converted, and the **budget sums converted home-currency amounts** — so you
  plan in USD with foreign costs counted correctly.
- **Tests:** 11 new (36 total).
- Verified: ruff/ty/pytest green; live Neon round-trip (migrate → create with
  per-leg caps → read back → delete; validator both ways) works; app loads clean.

**Next step**
- Rest of Phase 1: inline item editing + export to file. Then Phase 2: two-stage
  search (per-destination flight + hotel), budgeted against each stop's cap.

## 2026-09-03 — Expedia-style destination builder (from→to, required dates)

**What we did**
- **Schema** (`lets_go/schema.sql`): `legs` gains `from_city` + `from_country`
  (flight origin), added idempotently (`ADD COLUMN IF NOT EXISTS`) so existing
  Neon DBs migrate on startup. Verified live.
- **Data layer** (`lets_go/trips.py`): `DraftLeg` carries the origin;
  `create_trip`/`list_trips` read+write it. Validation reworked — dates are now
  **required**, **end must be after start** (no same-day/reversed), and a
  **departure city is required when "Need flight" is on**.
- **Plan tab:** rebuilt the create flow — destinations render as a list with an
  **"Add destination"** box beneath, each with **From city/From country
  (optional)** → **To city/Country** → a required **date-range** picker →
  need-flight/hotel. Receipts show **from → to**.
- **Tests:** date/flight rules updated + 4 new (11 trip tests; 25 total).
- Verified: ruff/ty/pytest green; live Neon round-trip (migrate → create with
  origin → read back → delete) works; app loads clean.

**Next step**
- Rest of Phase 1: inline item editing (move up/down, change day, edit price)
  and export to file. Then Phase 2: two-stage search (per-destination flight +
  hotel, budget-anchored).

## 2026-09-03 — Phase 1 slice 2: priced items + budget bar

**What we did**
- **Data layer** (`lets_go/trips.py`): `add_item`, `list_items`, `delete_item`
  (parameterized; items ordered by leg → day → position) plus a pure
  `validate_new_item` (name required, non-negative cost).
- **Budget math** (`lets_go/budget.py`): added `budget_progress` — cap fraction
  clamped to 0–1 for the progress bar (full when spent with no cap set).
- **Plan tab:** "Add items to a trip" — pick a saved trip, see a **live budget
  bar** (spent / cap · remaining, red when over), add items (type · name · cost ·
  city · day), and remove them. Restaurant costs marked "(est.)".
- **Tests:** 7 new unit tests for the pure helpers (21 total).
- Verified: ruff/ty/pytest green; live Neon round-trip (create trip → add 3 items
  → list → budget → delete → cascade cleanup) works; app loads clean (HTTP 200).

**Next step**
- Phase 1 slice 3: Plan-tab item editing (move up/down, change day, edit price
  inline) and Export to file. Currency conversion arrives with Phase 2.

## 2026-09-01 — Phase 1 slice 1: create & list trips

**What we did**
- **Schema** (`lets_go/schema.sql`): `trips`, `legs`, `items` tables; idempotent
  `init_db()` runs them on startup. Money stored in home currency for now.
- **Data layer** (`lets_go/trips.py`): pure helpers (`validate_new_trip`,
  `trip_date_range`) + DB access (`create_trip`, `list_trips`), parameterized.
- **Plan tab:** create a trip — name, home currency, budget cap, and add cities
  (with optional dates + need-flight/hotel), then save.
- **Receipts tab:** lists saved trips (name · cities · date span), expandable to
  show legs and budget cap.
- **Tests:** 8 new unit tests for the pure helpers (14 total).
- Verified: ruff/ty/pytest green; live Neon round-trip (create → read → delete)
  works; app loads clean.

**Next step**
- Phase 1 slice 2: add priced items to days + live budget bar vs cap.

## 2026-09-01 — Deployed to Streamlit Cloud (Phase 0 done)

**What we did**
- Added a uv-generated **`requirements.txt`** (Streamlit Cloud can't read uv's
  pyproject.toml); noted the regen step in `CLAUDE.md`.
- Removed Dependabot version-update config; kept **security alerts** on.
- Made the repo **public** (verified no secrets in git history first) so
  Streamlit Cloud could access it.
- **Deployed** on Streamlit Community Cloud with secrets set in the dashboard
  (app password + Neon URL). App is live and working — login + three tabs +
  "Neon connected".

**Phase 0 is complete.**

**Next step**
- Add to phone Home Screen (optional, anytime).
- Consider free **branch protection** now that the repo is public.
- Start **Phase 1:** first schema (trips/legs/items) + "create a trip" flow.

## 2026-09-01 — Phase 0 app skeleton (shell first)

**What we did**
- Added **streamlit** and **psycopg[binary]** (Neon/Postgres driver) via uv.
- **`app.py`:** login gate + three-tab layout (Plan / Receipts / Restaurants by
  city) with placeholder content.
- **`lets_go/auth.py`:** single-user password gate (constant-time compare;
  reads from secrets; empty password never authenticates).
- **`lets_go/db.py`:** one data-access layer — cached Neon connection +
  `health_check()` (`SELECT 1`); clear error if the URL isn't configured yet.
- **`.streamlit/secrets.toml.example`:** template for password + Neon URL (real
  `secrets.toml` is gitignored).
- **Neon wired up & live-tested:** connected to project `old-scene-25676334`
  (us-west-2). `health_check()` runs against the real DB (Postgres 18.6); app
  shows a "Neon connected ✅" status in the sidebar.
- Verified: ruff/ty/pytest green; app launches headless (HTTP 200), no errors,
  live DB health check passes.

**Next step**
- Design the **first schema** (trips/legs/items) — start of Phase 1.
- Deploy to **Streamlit Community Cloud** + test Add-to-Home-Screen (needs
  setting the same secrets in the Streamlit Cloud dashboard).
- Housekeeping: rotate the Neon password (it was shared in chat).

## 2026-08-31 — Tier 1 automations (secrets, deps, consistency)

**What we did**
- **Secret scanning:** added **gitleaks** (v8.30.1) as a pre-commit hook and a
  CI job — blocks committing keys/passwords/DB URLs, locally and on GitHub.
- **Dependabot** (`.github/dependabot.yml`): weekly PRs for Python deps (uv
  ecosystem) and GitHub Actions, incl. security updates.
- **`.editorconfig`:** consistent indentation/line-endings across editors.
- Verified all local hooks pass (gitleaks, ruff, ruff-format, ty, pytest).
- Note: **branch protection** on `main` (require CI to pass) is a GitHub repo
  setting, applied separately after this PR's checks exist.

**Next step**
- Enable branch protection on `main`; then begin **Phase 0 app skeleton**.

## 2026-08-31 — Tooling & CI setup (Phase 0 groundwork)

**What we did**
- Initialized the uv project (Python 3.12): `pyproject.toml`, `.python-version`,
  `.venv`, `uv.lock`.
- Added dev tools: **ruff, ty, pytest, prek** (`uv add --dev`).
- Configured **ruff** (line length 100; rules E/W/F/I/B/UP/SIM) and **pytest**
  (tests/ + pythonpath) in `pyproject.toml`; ty uses defaults.
- Added first real code + tests: `lets_go/budget.py` (pure budget math) and
  `tests/` with a `conftest.py` fixture — 6 tests pass.
- Two-layer checks wired up:
  - **Local:** `.pre-commit-config.yaml` (ruff, ruff-format, ty, pytest) via
    `prek install` — blocks bad commits.
  - **GitHub:** `.github/workflows/ci.yml` runs the same checks on push/PR,
    incl. `uv sync --locked` (fails on stale lockfile).
- Added `.gitignore` (ignores `.venv`, caches, and Streamlit secrets).
- Verified: ruff, ruff-format, ty, and pytest all green locally and via the hooks.

**Next step**
- Begin **Phase 0 app skeleton** from `TASKS.md`: three-tab Streamlit app,
  Neon connection + secrets, password login, first deploy.

## 2026-08-26 — Planning, requirements & task breakdown

**What we did**
- Set the working rule in `AGENT.md`: do not assume, ask, question me; no
  unrequested scope.
- Ran a requirements interview and confirmed the product direction. Key decisions:
  - Platform: **Streamlit** web app + **Add to Home Screen** for the phone-app
    feel; **$0** target.
  - Storage: **Neon** (free-tier Postgres) — permanent free, no card.
  - Access: **password login**. Backup: **export to file**.
  - Budget: single **cap**, **whole trip** across multiple cities; **one home
    currency**.
  - Trips: **multi-city**. Itinerary: **group by day**, ordered **by distance**.
  - Recommendations: **auto-search**, free sources; **preferred on top**, then
    **cheapest-first within budget**, lazy **"show all"**.
  - Restaurant cost: **per-city average** primary (marked), manual override;
    per-restaurant bracket deferred (not free).
  - Ratings: **good / ok / bad**, **multiple dated reviews** (latest wins);
    **Restaurants-by-city** tab (country→city, filters incl. **wishlist**).
  - Layout: three tabs — **Plan / Receipts / Restaurants by city**.
- **API reality-check** (§11 of PRD): flights free & workable (Travelpayouts);
  hotels free only at small volume (needs caching + manual fallback);
  per-restaurant price bracket **not** free.
- Wrote/updated docs: `AGENT.md`, `PRD.md` (full spec), `TASKS.md` (phased build
  plan), this `CHANGELOG.md`.

**Next step**
- Begin **Phase 0 (Foundations)** from `TASKS.md`: project scaffold, three-tab
  Streamlit skeleton, Neon connection + secrets, password login, first deploy +
  Add-to-Home-Screen check.
