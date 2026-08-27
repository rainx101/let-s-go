# CHANGELOG

Progress log for "let's go". **Rule:** entries by **date + topic**, newest at the
top → oldest at the bottom. Each entry records **what we did** and the **next
step**.

---

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
