# PRD — Travel Budget & Planning App ("let's go")

Status: **Confirmed direction** (from interview 2026-08-26). Build details still to
be worked out at implementation time. See `AGENT.md` — do not assume; ask.

Last updated: 2026-08-26

---

## 1. Problem / vision

The user needs a simple way to **plan a trip within a budget** — mainly around
**flights, hotels, and the spots they want to visit**. They enter **dates and a
budget range** and get **flight + hotel recommendations** to choose from (and can
decide up front whether they even need a flight and/or hotel). They can then
hand-type the **spots** they want to visit; the app helps arrange **when to go
where**, and the user can edit it. Adding **restaurants** lets the app help plan
by **distance**. Whole trips are **saved as a collection** (date range + place) to
revisit later. Hotels can be marked **preferred** so they resurface next time with
a "liked before" mark; restaurants are rated **like / ok / bad** to build a
per-city reference list, plus a **wishlist** of restaurants to try.

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

- **Trip** — name, one or more **cities/legs** each with a **date range**, and a
  **budget range**. Flags for whether flight/hotel are needed.
- **Flight** — belongs to a trip/leg; options with prices; one chosen; counts
  toward budget.
- **Hotel** — belongs to a trip/leg; options with prices; one chosen; counts
  toward budget; can be marked **preferred**.
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

## 9. Main flow (as described by the user)

1. **Main page = Plan.** Enter dates + budget range; choose if flight and/or hotel
   is needed; add cities/legs.
2. **Get recommendations.** Auto-search flights/hotels; user picks options.
3. **Add spots** (optional, hand-typed); app arranges them **by day, by distance**;
   user edits.
4. **Add restaurants**; app fits them in by distance; costs estimated.
5. **Budget** updates as items are chosen/added.
6. **Save trip** into the collection.
7. **After the trip / anytime:** rate restaurants like/ok/bad, mark hotels
   preferred, add to restaurant wishlist.
8. **Next time in the same city:** preferred hotels and rated restaurants resurface
   as recommendations with the "liked before" mark.

## 9a. Navigation / layout — DECIDED (2026-08-26)

Three main tabs:

1. **Plan** (main tab) — the working plan for a trip. The user can **move items
   around** (rearrange spots/restaurants across days) and **adjust a price**
   inline if a recommended/estimated one is inaccurate. This is where a trip is
   built and edited.

2. **Receipts** — a list of each saved trip's **receipt** (its collection entry).
   **Clicking a receipt opens the whole plan** for that trip. From the opened
   receipt the user can **add ratings** (rate restaurants, mark hotel preferred).

3. **Restaurants by city** — restaurants grouped **per city**. Navigation:
   **select country → city**, then results pop up. **Filters:** good / ok / bad /
   **wishlist**.
   - **Multiple visits/reviews per restaurant:** each review is dated by its
     **trip date**. A restaurant has an **expandable review section** listing all
     reviews **newest → oldest**. The restaurant's **current rating is the latest
     review's** rating.
   - **Wishlist** ("restaurants I want to try") lives in this tab but is kept
     **separate from rated restaurants** (its own filter).

Link between tabs: ratings entered on a **Receipt** flow into the
**Restaurants by city** list (good/ok/bad + trip-dated reviews) and into the
preferred-hotel memory used for future recommendations.

## 10. Remaining details to confirm at build time

1. Which specific flight + hotel APIs to start with (flights: Travelpayouts Data
   API confirmed viable in §11; hotels: pick from the small-quota free options).
2. Which free source supplies the per-city average meal cost.
3. Which free source provides currency conversion rates.

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
