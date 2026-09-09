# PRD — Travel Budget & Planning App ("let's go")

Status: **Confirmed direction** (interview 2026-08-26; flow revised 2026-09-03).
Build details still to be worked out at implementation time. See `AGENT.md` — do
not assume; ask.

Last updated: 2026-09-03

---

## 1. Problem / vision

The user needs a simple way to **plan a trip within a budget**. The app is a
**guided, budget-anchored flow** (revised 2026-09-03): first build the trip
**skeleton** (destinations, dates, overall budget, round-trip or one-way), then
add the **activities** they want to do (the "need" — fixed prices, searched when
possible, otherwise hand-typed), then plan **flight + hotel** against the budget
**left after activities**, leaving the **remainder for restaurants**. At the end
the user **generates a receipt** — the full day-by-day plan, where undated
activities get a recommended day, restaurants are placed **near the activities**,
and items can be **reordered**. Trips are held as a **draft** while planning and
**finalized** on save, then appear in the **Receipts** collection (still editable —
swap a hotel, hand-type the real amount paid). Hotels can be marked **preferred**
so they resurface next time with a "liked before" mark; restaurants are rated
**like / ok / bad** to build a per-city reference list, plus a **wishlist**.

## 2. Goals

- Enter **dates + budget range** → get **flight and hotel recommendations**.
- Choose up front whether a **flight and/or hotel** is needed.
- Hand-type **spots** to visit (optional); app arranges them **by day**, editable.
- Add **restaurants** → app helps plan **by distance**.
- Keep a **running budget** so the plan stays within range.
- **Save trips** as a browsable collection (date range + place).
- Mark **hotels preferred** → resurface as recommendations next time, marked
  "liked before".
- Rate **restaurants like / ok / bad** → per-city reference list.
- Keep a **wishlist** of restaurants to try.
- **Easy to use on a phone**; **free** to build and run.

## 3. Non-goals (for now)

- Not a booking engine — no reservations/payments.
- Not multi-user / social — single user assumed.
- Not guaranteed perfectly-accurate live prices (best-effort from free tiers).
- Not fully offline — app loads over the internet (see §5).

## 4. Users

- **Single user** (the owner).

## 5. Platform & delivery — DECIDED

- **Streamlit** web app (Python). Chosen for easiest build + free hosting.
- Used on phone via **"Add to Home Screen"** → gives an app icon that opens
  full-screen (the "download as an app" feel), no app store, $0. Caveat: needs
  internet to load; not a true offline installed app.
- **Storage: Neon** (free-tier Postgres) — **DECIDED**. Permanent free, no credit
  card, ~0.5 GB, commercial use allowed; scale-to-zero (brief wake after idle) but
  **does not pause/expire** like some free tiers. Holds trips, items, ratings,
  wishlist, preferences. User creates a free Neon account at build time.
- **Access:** **password login** — only the user can view/edit trips (safe for a
  public URL).
- **Backup/export:** provide a button to **export all trips + ratings to a file**,
  so data survives if a free service disappears.

## 6. Scope decisions — DECIDED (interview 2026-08-26)

- **Budget scope:** flight + hotel + spots count toward the budget total;
  restaurants are **estimated** (rough figure, still contributes but approximate).
- **Budget input:** a single **cap** (one number), not a min–max range. For a
  multi-city trip the cap covers the **whole trip** (all cities combined), and
  **inter-city flights/trains count as items**.
- **Trip type (revised 2026-09-03):** **round-trip** or **one-way**, on top of
  multi-city. Round-trip includes a **return flight to the origin** (its own
  date); one-way ends at the final destination.
- **Budget = flight + hotel; activities & food are extras (revised 2026-09-08b):**
  the budget the user sets is the **flight + hotel budget** — the amount for
  getting there and sleeping, and the **ceiling the Phase 3 search obeys**. Set
  **per destination** (each stop has its own flight+hotel budget; a POI-anchored
  hotel per city).
  - **Flight and hotel are separate steps, each shown only if that stop needs it**
    (need-flight / need-hotel). Optionally enter a **cap for each**; if blank, the
    flight+hotel budget **splits in half** as the two starting search ceilings; if
    **only one is needed, it takes the whole budget** (the driving-to-Disney case:
    no flight → the hotel gets it all).
  - **Activities and food are extras** — added freely, tracked in a running total
    **on top** of the flight+hotel budget, **not capped** and not pre-allocated.
    (Food does not get a fixed slice; it's whatever you add.)
  - The budget header shows the flight+hotel budget with the flight/hotel ceilings,
    plus the extras total. (Supersedes the 2026-09-08 per-city *waterfall*
    — activities-off-the-top → flight+hotel → food-remainder — which gave food an
    arbitrary half and never produced a clean per-item search ceiling.)
- **Currency:** one **home currency** chosen by the user; all costs convert to it
  and the budget cap is in it.
- **Recommendation results display:** **preferred / "liked before" shown on top
  with a mark**, then **cheapest first within budget**. An **option to "show all"**
  (including over-budget) is available but **not searched/expanded unless the user
  clicks it** (avoids extra API calls).
- **Restaurant cost estimate (revised after §11 reality-check):** the
  **per-city average meal cost is the PRIMARY estimate** (free sources exist),
  always **clearly marked "per-city average"**; the user can **override** with
  their own number anytime. A **per-restaurant price bracket** ($–$$$$) is a
  **deferred, optional** upgrade only if a billing-based place API (Google/
  Foursquare) is later accepted — not free, so not in the initial build.
- **Trip shape:** **multi-city** allowed — a trip can have several cities/legs,
  each with its own dates.
- **Destinations & hotel anchoring (revised 2026-09-08):** a destination is **any
  geocoded place, not only a city** — a point of interest works (e.g.
  **"Disneyland, Anaheim"**), Expedia-style. That place is the stop's **anchor**.
  - **Hotel is anchored to it:** the hotel recommendation ranks options by a
    **distance-to-anchor × price combo** (nearest *and* cheapest), within the
    flight+hotel budget (§6) — not cheapest-alone. Finding a good hotel near the
    anchor is often the **primary goal** of the stop (the driving-to-Disney case).
  - **Activities can scatter:** each activity keeps its **own geocoded point** and
    may sit far from the anchor (hotel near Disney/Anaheim, activities in LA). The
    plan uses distance from the anchor as a signal and can **group days by
    proximity** (an Anaheim day vs an LA day), rather than assuming one cluster.
  - Driving trips just turn **need-flight off**; the anchor + hotel + activities
    stand on their own. (All this is **Phase 3** — geocoding + hotel search;
    manual entry of a place and a hotel stays the always-available baseline.)
- **Itinerary detail:** **group spots by day** (Day 1, Day 2…), ordered **by
  distance** within each day. No fixed clock times. Fully editable.
- **Recommendations:** **auto-search from day one** using **free-tier APIs**. User
  will **register the required free API accounts/keys**. Realistic fallback:
  where a free source doesn't cover something (some hotels especially), allow
  **quick manual entry** so the app still works and stays $0.
- **Locations & distance:** places (spots/restaurants) are **auto-located by name**
  using free **OpenStreetMap** geocoding; the app uses **map distance** to order
  each day's plan. (Distance is available for free, so it's included.)
- **Ratings:** restaurants rated **good / ok / bad**, kept as a **per-city list**.
  A restaurant can have **multiple dated reviews** (by trip date), shown newest →
  oldest in an expandable section; the **current rating = the latest review**.
- **Wishlist:** **restaurants I want to try**, kept in the Restaurants-by-city tab
  but **separate** from rated restaurants (own filter).
- **Preferred hotels:** markable as preferred → resurface in recommendations for
  the same area with a **"liked before"** mark.

## 7. Core concepts / data model (draft — confirm at build)

- **Trip** — name, **type** (round-trip / one-way), one or more **destinations/
  legs** each with a **date range**, an overall **budget cap**, and a **status**
  (**draft** while planning → **final** on save). Flags for whether flight/hotel
  are needed. (Revised 2026-09-03.)
- **Destination (leg)** — a **place, not only a city**: a free-text name that
  Phase 3 **geocodes to a point** (a POI like "Disneyland" is valid). That point
  is the stop's **anchor** for hotel search and distance (§6, revised 2026-09-08).
- **Activity** — a fixed-price thing to do; assigned to a day (day optional until
  the receipt recommends one); **searched when possible, else hand-typed**; the
  first budget category in the waterfall (§6).
- **Item cost** — every priced item keeps an **editable amount**; an auto/searched
  value is an **estimate** the user can replace with the **real amount paid** so
  the receipt budget is accurate (§9 step 6).
- **Flight** — belongs to a trip/leg; options with prices; one chosen; counts
  toward budget.
- **Hotel** — belongs to a trip/leg; options with prices **and locations**; one
  chosen; counts toward budget; can be marked **preferred**. Search ranks options
  by **distance-to-anchor × price** within the flight+hotel budget (§6), not price
  alone.
- **Spot** — a place to visit; located by name; assigned to a day; counts toward
  budget.
- **Restaurant** — located by name; can be added to a day (distance-planned);
  **estimated** cost; rateable **like/ok/bad**; can live on the **wishlist**.
- **Saved trips collection** — all trips, browsable by date range + place.
- **Preferred / rated library** — hotels (preferred) and restaurants (rated),
  scoped **per city**, resurfaced when planning the same area again.

## 8. Data sources (research, 2026-08-26)

- No single permanent free API gives Expedia-level accurate live prices; free
  options are small quotas (signup + key) or unofficial scrapers that can break.
- **Amadeus Self-Service** (former free go-to) **shut down 2026-07-17** — not
  usable.
- Current free-tier candidates to evaluate at build time:
  - Flights: Travelpayouts Data API; Kiwi/Duffel (limited free calls).
  - Hotels: SearchAPI Google Hotels (100 free); ScrapeBadger (~1,000 credits);
    Xotelo (no key, unofficial); Makcorps (small free quota).
  - Maps/geocoding/distance: **OpenStreetMap** (free, used for locations +
    distance).
- Personal-scale volume means these free tiers are realistically enough at $0.

Sources:
- https://thunderbit.com/blog/best-flight-api-with-free-tiers
- https://developers.amadeus.com/blog/new-self-service-pricing-amadeus-api
- https://stayapi.com/blog/free-hotel-api
- https://xotelo.com/
- https://www.searchapi.io/google-hotels-api

## 9. Main flow — per-destination planning (revised 2026-09-03, as built)

A trip is a **draft** while being built and **finalized** when done. All
creating/editing happens in the **Plan** tab; **Receipts** holds finalized trips.

1. **Plan a trip (skeleton).** Name, home currency, overall **budget cap** (required),
   then add **destinations** — each a **From → To** (with a per-card **round-trip /
   one-way** toggle), **required non-overlapping dates**, an optional **per-stop
   budget**, and need-flight/hotel flags. Destinations are editable, and the next
   card's "From" auto-fills from where the last leg leaves you. **Start planning**
   saves the trip as a **draft** and opens the planner.
2. **Plan per destination — step wizard (revised 2026-09-08b).** You plan **city
   by city**; within a city a **Next/Back** wizard steps through **Flight → Hotel
   → Activities → Food**, showing the **flight+hotel budget bar on top** and the
   destination's **time frame**. **Flight and Hotel are separate steps, shown only
   if the stop needs them** (need-flight/hotel), and each can take an optional cap
   (else the budget splits ½/½; one-needed takes all). **Activities and food are
   extras** added on top (§6). Items are auto-assigned to the stop; **cost is
   optional** (blank = TBD); **day optional**; any currency → home; restaurants
   marked as estimates. Costs are hand-typed now; **auto-search** (incl. the
   anchor-ranked hotel search, §6) fills them in Phase 3, always user-editable.
   **Next** past the last stop opens **Review**.
3. **Review.** The whole-trip plan and running budget; finish with **Save as
   draft** or **Finalize**.
4. **Receipts.** Finalized trips only — expand for the **read-only** plan +
   budget; **Delete** (with confirm).
5. **Editing** (all in the **Plan** tab): **Drafts** (Edit → keep planning /
   Delete) and **Edit a finalized trip** (pick one → reopens for editing).
6. **Phase 3 additions:** flight/hotel/activity **auto-search** — incl.
   **anchor-ranked hotel search** (nearest-to-the-destination-place × price, §6);
   **geocoded place destinations** (a POI, not just a city); **distance** ordering
   (restaurants near activities; days grouped by proximity); **recommend a day**
   for undated activities; **reorder** items; on a finalized receipt, **rate**
   restaurants and mark hotels **preferred**; these resurface with a "liked
   before" mark next time in the same area.

## 9a. Navigation / layout (revised 2026-09-03, as built)

Three tabs:

1. **Plan** — everything about creating and editing a trip. Not planning:
   **Plan a trip** (new), **Drafts** (Edit / Delete), **Edit a finalized trip**
   (pick → edit). Editing opens a **Setup** view (name / budget / destinations),
   then **Start planning** enters the **per-city step wizard** (Activities →
   Flight/Hotel → Restaurants) and **Review** (Save as draft / Finalize). Item
   prices are **user-editable** inline. Editing always stays in this tab.

2. **Receipts** — **finalized trips only**, read-only: expand for the full plan +
   budget, then **Delete** (confirm). (Ratings / preferred marks on an opened
   receipt arrive in Phase 3.)

3. **Restaurants by city** (Phase 3) — restaurants grouped per city; select
   **country → city**; filters **good / ok / bad / wishlist**; expandable
   **dated reviews** newest → oldest (**latest review wins**); wishlist kept
   separate.

Link between tabs (Phase 3): ratings entered on a receipt flow into the
**Restaurants by city** list and the preferred-hotel memory for recommendations.

## 10. Remaining details to confirm at build time

1. Which specific flight + hotel APIs to start with (flights: Travelpayouts Data
   API confirmed viable in §11; hotels: pick from the small-quota free options).
2. Which free source supplies the per-city average meal cost.
3. Which free source provides currency conversion rates.
4. Whether any free/affordable source can supply **activity prices** (tickets/
   tours); if not, **hand-type stays the baseline** (§11).

## 11. API reality-check (results, 2026-08-26)

Goal: confirm before writing tasks that free flight/hotel auto-search actually
returns usable data at $0.

- **Flights — WORKS, free.** Travelpayouts/Aviasales **Data API**: free with
  affiliate signup + token. Returns **cached cheapest prices** per route/date
  (from real searches, kept ~7 days), incl. a **calendar** endpoint (cheapest per
  day of month). Ballpark, not live-exact — **good enough for budgeting**. Note:
  old endpoint version **retires 2026-06-15**; use the current one.
- **Hotels — WORKS only at small volume.** Free tiers are tiny: StayAPI (~50
  requests, broad coverage, "evaluation volume not production"), StayingAPI (free,
  no card), Makcorps (~30). Unofficial no-key option (Xotelo) did not respond when
  pinged — unreliable. **OK for personal scale IF results are cached and manual
  price entry is always available as fallback.**
- **Per-restaurant price bracket — NOT reliably free.** Foursquare free tier
  excludes price/rating (Premium, billed from first call); Google Places needs a
  billing account. → Design uses **per-city average as primary** (see §6);
  per-restaurant bracket deferred.
- **Activity prices — wanted, but no clean free source (evaluate at build).**
  The user would prefer the app to **search activity/ticket prices** rather than
  hand-type. Realistically, general activity-price data (tickets, tours) is the
  same story as hotels/restaurants: paid or narrow free tiers. → Treat activity
  search as a **best-effort, cache-and-fallback** feature; **hand-typing a fixed
  price remains the reliable baseline** so the flow never blocks (§9 step 2).
- **Design implications:**
  - Cache API results; every auto-priced field must be **user-editable**.
  - Lazy-search (don't fetch over-budget/"show all" unless clicked) to conserve
    quota.
  - Keep a clean **manual-entry fallback** for every price so the app never breaks
    when a free tier is exhausted or down.

Sources:
- https://support.travelpayouts.com/hc/en-us/articles/203956163-Aviasales-Data-API
- https://thunderbit.com/blog/best-flight-api-with-free-tiers
- https://stayapi.com/blog/free-hotel-api
- https://docs.foursquare.com/developer/reference/upcoming-changes
