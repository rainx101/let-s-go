# Mockups

Static, clickable UI mockups for direction — **not** the app. Open the `.html`
files in a browser.

## `plan-flow.html` — the planning flow (simple)

Approved direction for the plan flow, using the driving-to-Disney example.

- **Screen 1 · Setup (skeleton):** trip name, home currency, destinations. A
  destination is **any place, not just a city** ("Disneyland, Anaheim") — the hint
  says we anchor the hotel to it. Each destination has a **flight + hotel budget**
  (the search ceiling) with optional ✈️ flight / 🏨 hotel caps (blank = split ½).
  Need-flight/hotel toggles; driving = flight off. **▶ Start planning** → steps.
- **Screen 2 · Plan steps (per city):** wizard **Flight → Hotel → Activities →
  Food**; Flight/Hotel are **separate steps shown only if needed** (driving = ✈️
  struck through). Budget bar on top shows the flight+hotel budget + the extras
  total. **Review → Finalize** splits *within budget* (hotel) from *extras*
  (activities + food).
- **Budget model (approved 2026-09-08b):** the budget is **flight + hotel** (the
  search ceiling); **activities & food are extras** added on top, not capped. Only
  one of flight/hotel needed → it takes the whole budget.
- **Hotel step recommendation is a Phase-3 placeholder:** hotels near the anchor
  ranked by **distance + price**, under the hotel budget. Manual "add a hotel" is
  the fallback.

Reflects PRD §6 (flight+hotel budget, extras), §7 (place/POI destinations,
anchor-ranked hotels), and the city-by-city step wizard.

Live artifact (may change): https://claude.ai/code/artifact/d68e3e5f-d3cd-4f51-995a-f00b9f68dd2c
