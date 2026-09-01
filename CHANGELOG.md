# CHANGELOG

Progress log for "let's go". **Rule:** entries by **date + topic**, newest at the
top → oldest at the bottom. Each entry records **what we did** and the **next
step**.

---

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
