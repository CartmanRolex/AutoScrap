import sqlite3
import pathlib

DB_PATH = pathlib.Path("data/autoscrap.db")

_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS listings (
    -- Identity
    id                      TEXT PRIMARY KEY,
    source                  TEXT NOT NULL DEFAULT 'autoscout24',
    url                     TEXT NOT NULL,
    version_full_name       TEXT,
    condition_type          TEXT,       -- used / new / pre-registered
    vehicle_category        TEXT,
    body_type               TEXT,
    color                   TEXT,
    doors                   INTEGER,

    -- Make / model
    make_id                 INTEGER,
    make_name               TEXT,
    make_key                TEXT,
    model_id                INTEGER,
    model_name              TEXT,
    model_key               TEXT,

    -- Performance & specs
    horse_power             INTEGER,
    kilo_watts              INTEGER,
    fuel_type               TEXT,
    transmission_type       TEXT,
    transmission_type_group TEXT,
    mileage                 INTEGER,    -- km
    range_km                INTEGER,    -- electric range km
    consumption_combined    REAL,       -- L/100km or kWh/100km

    -- Registration & history
    first_registration_date TEXT,       -- YYYY-MM-DD
    first_registration_year INTEGER,
    had_accident            INTEGER,    -- 0/1 boolean
    inspected               INTEGER,    -- 0/1 boolean
    has_additional_tires    INTEGER,    -- 0/1 boolean
    has_new_tires           INTEGER,    -- 0/1 boolean

    -- Price
    price_chf               INTEGER,
    previous_price_chf      INTEGER,
    leasing_monthly_chf     REAL,

    -- Seller
    seller_id               INTEGER,
    seller_name             TEXT,
    seller_type             TEXT,       -- professional / private
    seller_city             TEXT,
    seller_zip              TEXT,
    latitude                REAL,
    longitude               REAL,

    -- Warranty
    warranty_type           TEXT,       -- from-first-registration / from-delivery

    -- Description
    teaser                  TEXT,

    -- Timestamps from AutoScout24
    as24_created_at         TEXT,       -- ISO-8601 UTC
    as24_modified_at        TEXT,       -- ISO-8601 UTC

    -- Our tracking timestamps
    first_seen_at           TEXT NOT NULL,  -- ISO-8601 UTC
    last_seen_at            TEXT NOT NULL,  -- ISO-8601 UTC
    is_active               INTEGER NOT NULL DEFAULT 1,

    -- Full raw JSON for forward-compatibility
    raw_json                TEXT
);
"""

_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_source           ON listings(source);
CREATE INDEX IF NOT EXISTS idx_make_model       ON listings(make_key, model_key);
CREATE INDEX IF NOT EXISTS idx_price            ON listings(price_chf);
CREATE INDEX IF NOT EXISTS idx_first_seen       ON listings(first_seen_at);
CREATE INDEX IF NOT EXISTS idx_as24_created     ON listings(as24_created_at);
CREATE INDEX IF NOT EXISTS idx_condition        ON listings(condition_type);
CREATE INDEX IF NOT EXISTS idx_fuel             ON listings(fuel_type);
CREATE INDEX IF NOT EXISTS idx_seller           ON listings(seller_id);
"""

_MIGRATIONS = {
    "source": "ALTER TABLE listings ADD COLUMN source TEXT NOT NULL DEFAULT 'autoscout24'",
    "body_type": "ALTER TABLE listings ADD COLUMN body_type TEXT",
    "color": "ALTER TABLE listings ADD COLUMN color TEXT",
    "doors": "ALTER TABLE listings ADD COLUMN doors INTEGER",
    "latitude": "ALTER TABLE listings ADD COLUMN latitude REAL",
    "longitude": "ALTER TABLE listings ADD COLUMN longitude REAL",
}


def _migrate_listing_table(conn: sqlite3.Connection) -> None:
    existing_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(listings)").fetchall()
    }
    for column, statement in _MIGRATIONS.items():
        if column not in existing_columns:
            conn.execute(statement)


def init_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_TABLE_DDL)
    _migrate_listing_table(conn)
    conn.executescript(_INDEX_DDL)
    conn.commit()
    return conn
