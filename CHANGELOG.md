# CHANGELOG

Progress log for "let's go". **Rule:** entries by **date + topic**, newest at the
top → oldest at the bottom. Each entry records **what we did** and the **next
step**.

---

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
