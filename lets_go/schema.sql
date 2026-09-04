-- Schema for "let's go". Idempotent: safe to run on every startup.
-- Money is stored in the trip's home currency (conversion is Phase 2); the
-- `currency` column on items is reserved for the original currency later.

CREATE TABLE IF NOT EXISTS trips (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    home_currency TEXT NOT NULL DEFAULT 'USD',
    budget_cap    NUMERIC(12, 2),
    trip_type     TEXT NOT NULL DEFAULT 'round_trip',
    status        TEXT NOT NULL DEFAULT 'final',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Added after the initial trips table shipped; idempotent for existing DBs.
-- status defaults to 'final' so pre-existing trips read as finished; the guided
-- flow creates new trips as 'draft'.
ALTER TABLE trips ADD COLUMN IF NOT EXISTS trip_type TEXT NOT NULL DEFAULT 'round_trip';
ALTER TABLE trips ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'final';

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
ALTER TABLE legs ADD COLUMN IF NOT EXISTS round_trip BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS items (
    id         SERIAL PRIMARY KEY,
    trip_id    INTEGER NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
    leg_id     INTEGER REFERENCES legs (id) ON DELETE CASCADE,
    category   TEXT NOT NULL,
    name       TEXT NOT NULL,
    cost       NUMERIC(12, 2) NOT NULL DEFAULT 0,
    currency   TEXT,
    day        INTEGER,
    on_date    DATE,
    position   INTEGER NOT NULL DEFAULT 0,
    status     TEXT NOT NULL DEFAULT 'planned',
    notes      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Items are scheduled on a real DATE (within the destination's stay), not a
-- day-number. Added after the initial items table shipped; idempotent.
ALTER TABLE items ADD COLUMN IF NOT EXISTS on_date DATE;

CREATE INDEX IF NOT EXISTS idx_legs_trip ON legs (trip_id);
CREATE INDEX IF NOT EXISTS idx_items_trip ON items (trip_id);
