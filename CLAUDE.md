# CLAUDE.md

Coding rules for "let's go". Read with `AGENT.md` (do not assume; ask) and
`PRD.md` (spec). Stack: **Python · Streamlit · Neon (Postgres) · pytest**.
Tooling: **uv · ruff · ty · prek · pytest**.

## Tooling & environment
- Use **uv** for everything Python. Run tools with **`uv run python ...`** (and
  `uv run pytest`, `uv run ruff`, etc.) — never a bare system `python`.
- **Do not edit `pyproject.toml` dependencies by hand.** Add deps with
  **`uv add LIB`** (runtime) or **`uv add --dev LIB`** (dev/test).
- After any `uv add`, **commit the updated `uv.lock`** (project-root lockfile; or
  `backend/uv.lock` if we split a backend) — a stale lockfile fails CI.
- Streamlit Cloud can't read uv's `pyproject.toml`, so we also keep a generated
  **`requirements.txt`**. After changing deps, regenerate it:
  `uv export --no-dev --no-hashes --no-emit-project -o requirements.txt` and
  commit it.
- **ruff** for lint/format: `uv run ruff check` and `uv run ruff format`.
- **ty** for type-checking: `uv run ty` must pass.
- **prek** manages pre-commit hooks; install once and let it gate commits.
- **Logging, not print:** use the `logging` module so behavior is traceable when
  debugging; log at sensible levels (debug for detail, info for milestones,
  warning/error for problems).
- **Do not hide or wrap errors.** No swallowing exceptions, no broad catch-and-
  continue, no re-wrapping that loses the traceback. Let errors surface loudly;
  handle only the specific, expected ones (see Python rules).

## Work Style
For any code change:
1. Show a plan (what files, what changes, why) and wait for approval before touching anything.
2. Execute only what was approved — no extras.
3. Self-check after each change (verify the edit landed correctly, confirm no broken imports or structure).
4. Report back: what changed, what to watch for, what's next (if anything).

## Code Minimalism
- Plan first (3-5 bullets) for non-trivial changes; wait for confirmation.
- Reuse existing patterns (db helper, Streamlit tab layout, cached queries) —
  don't invent new abstractions without flagging why the existing one doesn't fit.
- Smallest diff that solves the task. No speculative handling, config, or
  params "for later."
- No comments restating code; no try/catch on things that can't throw.
- One file/function at a time for non-trivial work.
- Self-review before presenting: could anything here be deleted or inlined?
  Flag single-use functions/files.

## Python
- Standard library first; add a dependency only when it earns its place, via
  `uv add` (never hand-edit `pyproject.toml`).
- Follow PEP 8 (enforced by ruff); keep functions small and single-purpose. Use
  type hints on function signatures (checked by ty).
- Prefer pure functions for logic (budget math, distance, currency) so they're
  testable without Streamlit or the DB.
- No bare `except:`; catch the specific expected exception, and only where it can
  occur. Otherwise **let it propagate** — do not hide or wrap errors.
- Keep secrets out of code — read from Streamlit secrets / env only.

## Streamlit (UI)
- UI stays thin: it calls logic/data functions; no business rules or SQL inline
  in the page.
- Cache external/DB reads with `st.cache_data` / `st.cache_resource`; never cache
  secrets or per-user mutable state wrongly.
- Use `st.session_state` for in-session state; persist real data to Neon, not to
  session state.
- Match the three-tab structure (Plan / Receipts / Restaurants by city); reuse
  shared widgets rather than duplicating.
- Every auto-filled value (prices, estimates) must stay **user-editable**
  (PRD §11).

## Database (Neon / Postgres)
- All DB access goes through one small data-access layer (a `db.py`-style module);
  pages never open raw connections.
- **Parameterized queries only** — never string-format user input into SQL.
- Schema changes are explicit and versioned (a `schema.sql` / migration file);
  note them in `CHANGELOG.md`.
- Connection string comes from secrets; handle Neon's brief cold-start on idle.

## External APIs (flights / hotels / geocoding / currency)
- One thin client module per provider; the rest of the app depends on our own
  interface, not the vendor's response shape.
- Always: **cache** responses, **rate-limit** (OpenStreetMap ~1 req/s + user
  agent), and provide a **manual fallback** so the app works when a free tier is
  down/exhausted (PRD §11).
- Keys in secrets only. Fail soft: an API error shows an empty/edit state, never
  a crash.

## Tests (pytest, TDD)
- **TDD:** write the failing test first, then the code to pass it. Run with
  `uv run pytest`.
- Test the logic that can break: budget totals, currency conversion, distance
  ordering, "latest review wins," recommendation sort (preferred-first,
  cheapest-first).
- **DRY with fixtures in `conftest.py`** — shared setup (sample trip, mock DB,
  mock API responses) lives there, not copy-pasted per test.
- Pure functions get plain unit tests; **mock** external APIs and the DB — no
  live network or real Neon calls in the test suite.
- Name tests `test_<unit>_<behavior>`; one behavior per test; cover the edge case
  that motivated the code (empty results, over-budget, quota exhausted).
- Add or update a test with any logic change.

## Definition of done (per change)
- Edit landed, imports/structure intact.
- `uv run ruff check`, `uv run ty`, and `uv run pytest` all green.
- `uv.lock` committed if deps changed. Secrets clean (nothing committed).
- `CHANGELOG.md` updated when meaningful.
- Reported back: what changed, what to watch, what's next.

_Last updated: 2026-08-26_
