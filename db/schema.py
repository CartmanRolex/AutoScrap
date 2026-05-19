import sqlite3
import pathlib

DB_PATH = pathlib.Path("data/autoscrap.db")

_DDL = """
CREATE TABLE IF NOT EXISTS listings (
    id              TEXT PRIMARY KEY,
    url             TEXT NOT NULL,
    title           TEXT,
    make            TEXT,
    model           TEXT,
    year            INTEGER,
    mileage_km      INTEGER,
    price_chf       INTEGER,
    fuel_type       TEXT,
    transmission    TEXT,
    body_type       TEXT,
    power_hp        INTEGER,
    location        TEXT,
    seller_type     TEXT,
    image_url       TEXT,
    raw_json        TEXT,
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL,
    is_active       INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_listings_make_model ON listings(make, model);
CREATE INDEX IF NOT EXISTS idx_listings_price      ON listings(price_chf);
CREATE INDEX IF NOT EXISTS idx_listings_first_seen ON listings(first_seen_at);
"""


def init_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(_DDL)
    conn.commit()
    return conn
