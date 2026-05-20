import sqlite3
import pathlib
import json
import re

DB_PATH = pathlib.Path("data/autoscrap.db")

_AUTOSCOUT_ID_RE = re.compile(r"[?&]utm_term=(\d+)|autoscout24\.ch/[^?#]*?(\d{6,})(?:[/?#]|$)")

_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS listings (
    -- Identity
    id                      TEXT PRIMARY KEY,
    source                  TEXT NOT NULL DEFAULT 'autoscout24',
    canonical_id            TEXT,
    external_source         TEXT,
    external_id             TEXT,
    external_url            TEXT,
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
CREATE INDEX IF NOT EXISTS idx_canonical        ON listings(canonical_id);
CREATE INDEX IF NOT EXISTS idx_external         ON listings(external_source, external_id);
CREATE INDEX IF NOT EXISTS idx_make_model       ON listings(make_key, model_key);
CREATE INDEX IF NOT EXISTS idx_price            ON listings(price_chf);
CREATE INDEX IF NOT EXISTS idx_first_seen       ON listings(first_seen_at);
CREATE INDEX IF NOT EXISTS idx_as24_created     ON listings(as24_created_at);
CREATE INDEX IF NOT EXISTS idx_condition        ON listings(condition_type);
CREATE INDEX IF NOT EXISTS idx_fuel             ON listings(fuel_type);
CREATE INDEX IF NOT EXISTS idx_seller           ON listings(seller_id);

CREATE VIEW IF NOT EXISTS deduped_listings AS
WITH ranked AS (
    SELECT
        listings.*,
        ROW_NUMBER() OVER (
            PARTITION BY COALESCE(canonical_id, id)
            ORDER BY
                CASE source
                    WHEN 'autoscout24' THEN 0
                    ELSE 1
                END,
                first_seen_at
        ) AS dedupe_rank
    FROM listings
    WHERE is_active = 1
)
SELECT *
FROM ranked
WHERE dedupe_rank = 1;
"""

_MIGRATIONS = {
    "source": "ALTER TABLE listings ADD COLUMN source TEXT NOT NULL DEFAULT 'autoscout24'",
    "canonical_id": "ALTER TABLE listings ADD COLUMN canonical_id TEXT",
    "external_source": "ALTER TABLE listings ADD COLUMN external_source TEXT",
    "external_id": "ALTER TABLE listings ADD COLUMN external_id TEXT",
    "external_url": "ALTER TABLE listings ADD COLUMN external_url TEXT",
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


def _autoscout_id_from_url(url: str | None) -> str | None:
    if not url:
        return None
    match = _AUTOSCOUT_ID_RE.search(url)
    if not match:
        return None
    return next((group for group in match.groups() if group), None)


def _anibis_external_metadata(raw_json: str | None) -> tuple[str | None, str | None, str | None]:
    if not raw_json:
        return None, None, None

    try:
        raw = json.loads(raw_json)
    except json.JSONDecodeError:
        return None, None, None

    search = raw.get("search") or {}
    detail = raw.get("detail") or {}
    reply_platform = ((detail.get("replyInfo") or {}).get("externalPlatform") or {})
    external_url = (
        reply_platform.get("externalURL")
        or detail.get("externalURL")
        or search.get("externalURL")
    )
    formatted_source = (
        reply_platform.get("label")
        or detail.get("formattedSource")
        or search.get("formattedSource")
    )

    autoscout_id = _autoscout_id_from_url(external_url)
    if autoscout_id or formatted_source == "autoscout24.ch":
        return "autoscout24", autoscout_id, external_url

    return None, None, external_url


def _backfill_dedupe_metadata(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT id, source, raw_json
        FROM listings
        WHERE canonical_id IS NULL
           OR (source = 'anibis' AND external_source IS NULL AND raw_json IS NOT NULL)
        """
    ).fetchall()

    for row in rows:
        canonical_id = row["id"]
        external_source = None
        external_id = None
        external_url = None

        if row["source"] == "anibis":
            external_source, external_id, external_url = _anibis_external_metadata(row["raw_json"])
            if external_source == "autoscout24" and external_id:
                canonical_id = external_id

        conn.execute(
            """
            UPDATE listings
            SET canonical_id = COALESCE(canonical_id, ?),
                external_source = COALESCE(external_source, ?),
                external_id = COALESCE(external_id, ?),
                external_url = COALESCE(external_url, ?)
            WHERE id = ?
            """,
            (canonical_id, external_source, external_id, external_url, row["id"]),
        )


def init_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_TABLE_DDL)
    _migrate_listing_table(conn)
    _backfill_dedupe_metadata(conn)
    conn.executescript(_INDEX_DDL)
    conn.commit()
    return conn
