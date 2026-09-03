-- Schema for "let's go". Idempotent: safe to run on every startup.
-- Money is stored in the trip's home currency (conversion is Phase 2); the
-- `currency` column on items is reserved for the original currency later.

CREATE TABLE IF NOT EXISTS trips (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    home_currency TEXT NOT NULL DEFAULT 'USD',
    budget_cap    NUMERIC(12, 2),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS legs (
    id           SERIAL PRIMARY KEY,
    trip_id      INTEGER NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
    city         TEXT NOT NULL,
    country      TEXT,
    from_city    TEXT,
    from_country TEXT,
    start_date   DATE,
    end_date     DATE,
    need_flight  BOOLEAN NOT NULL DEFAULT FALSE,
    need_hotel   BOOLEAN NOT NULL DEFAULT FALSE,
    budget_cap   NUMERIC(12, 2),
    position     INTEGER NOT NULL DEFAULT 0
);

-- Added after the initial legs table shipped; idempotent for existing DBs.
ALTER TABLE legs ADD COLUMN IF NOT EXISTS from_city TEXT;
ALTER TABLE legs ADD COLUMN IF NOT EXISTS from_country TEXT;
ALTER TABLE legs ADD COLUMN IF NOT EXISTS budget_cap NUMERIC(12, 2);

CREATE TABLE IF NOT EXISTS items (
    id         SERIAL PRIMARY KEY,
    trip_id    INTEGER NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
    leg_id     INTEGER REFERENCES legs (id) ON DELETE CASCADE,
    category   TEXT NOT NULL,
    name       TEXT NOT NULL,
    cost       NUMERIC(12, 2) NOT NULL DEFAULT 0,
    currency   TEXT,
    day        INTEGER,
    position   INTEGER NOT NULL DEFAULT 0,
    status     TEXT NOT NULL DEFAULT 'planned',
    notes      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_legs_trip ON legs (trip_id);
CREATE INDEX IF NOT EXISTS idx_items_trip ON items (trip_id);
