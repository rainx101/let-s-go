# Mockups

Static, clickable UI mockups for direction — **not** the app. Open the `.html`
files in a browser.

## `plan-flow.html` — the planning flow (simple)

Approved direction for the plan flow, using the driving-to-Disney example.

- **Screen 1 · Setup (skeleton):** trip name, home currency, budget cap, and
  destinations. A destination is **any place, not just a city** ("Disneyland,
  Anaheim") — the hint says we anchor the hotel to it. Need-flight/hotel toggles;
  driving = flight off. **▶ Start planning** → the steps.
- **Screen 2 · Plan steps (per city):** simple 3-step wizard **Activities →
  Hotel → Food**, budget bar on top (activities / hotel / food segments), then
  **Review → Finalize**.
- **Step 2 hotel recommendation is a Phase-3 placeholder:** hotels near the
  anchor ranked by **distance + price**, within the per-city hotel budget
  (half-default). Example data, marked as such; manual "add a hotel" is the
  fallback.

Reflects the decisions in PRD §6/§7 (per-city waterfall budget, place/POI
destinations, anchor-ranked hotels) and the city-by-city step wizard.

Live artifact (may change): https://claude.ai/code/artifact/d68e3e5f-d3cd-4f51-995a-f00b9f68dd2c
