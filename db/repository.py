import sqlite3
from datetime import datetime, timezone

_LISTING_COLUMNS = (
    "id",
    "source",
    "url",
    "version_full_name",
    "condition_type",
    "vehicle_category",
    "body_type",
    "color",
    "doors",
    "make_id",
    "make_name",
    "make_key",
    "model_id",
    "model_name",
    "model_key",
    "horse_power",
    "kilo_watts",
    "fuel_type",
    "transmission_type",
    "transmission_type_group",
    "mileage",
    "range_km",
    "consumption_combined",
    "first_registration_date",
    "first_registration_year",
    "had_accident",
    "inspected",
    "has_additional_tires",
    "has_new_tires",
    "price_chf",
    "previous_price_chf",
    "leasing_monthly_chf",
    "seller_id",
    "seller_name",
    "seller_type",
    "seller_city",
    "seller_zip",
    "latitude",
    "longitude",
    "warranty_type",
    "teaser",
    "as24_created_at",
    "as24_modified_at",
    "first_seen_at",
    "last_seen_at",
    "is_active",
    "raw_json",
)

_UPDATE_COLUMNS = tuple(
    column for column in _LISTING_COLUMNS if column not in {"id", "first_seen_at"}
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _listing_record(listing: dict, now: str) -> dict:
    record = dict.fromkeys(_LISTING_COLUMNS)
    record.update(listing)
    record["source"] = record.get("source") or "autoscout24"
    record["first_seen_at"] = now
    record["last_seen_at"] = now
    record["is_active"] = 1
    return record


def upsert_listing(conn: sqlite3.Connection, listing: dict) -> bool:
    """Insert a new listing or update last_seen_at on duplicate. Returns True if new."""
    now = _now()
    exists = listing_exists(conn, listing["id"])
    columns_sql = ", ".join(_LISTING_COLUMNS)
    values_sql = ", ".join(f":{column}" for column in _LISTING_COLUMNS)
    update_sql = ",\n                ".join(
        f"{column} = excluded.{column}" for column in _UPDATE_COLUMNS
    )

    try:
        conn.execute(
            f"""
            INSERT INTO listings ({columns_sql})
            VALUES ({values_sql})
            ON CONFLICT(id) DO UPDATE SET
                {update_sql}
            """,
            _listing_record(listing, now),
        )
        conn.commit()
        return not exists
    except sqlite3.Error:
        conn.rollback()
        raise


def listing_exists(conn: sqlite3.Connection, listing_id: str) -> bool:
    return (
        conn.execute("SELECT 1 FROM listings WHERE id = ? LIMIT 1", (listing_id,)).fetchone()
        is not None
    )


def touch_listing(conn: sqlite3.Connection, listing_id: str) -> bool:
    cur = conn.execute(
        "UPDATE listings SET last_seen_at = ?, is_active = 1 WHERE id = ?",
        (_now(), listing_id),
    )
    conn.commit()
    return cur.rowcount > 0


def count_listings(conn: sqlite3.Connection, source: str | None = None) -> int:
    if source is None:
        return conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    return conn.execute(
        "SELECT COUNT(*) FROM listings WHERE source = ?", (source,)
    ).fetchone()[0]


def mark_inactive(
    conn: sqlite3.Connection, ids_to_keep: list[str], source: str | None = None
) -> int:
    """Mark all listings not in ids_to_keep as inactive (no longer in results)."""
    if not ids_to_keep:
        return 0
    placeholders = ",".join("?" * len(ids_to_keep))
    params: list[str] = list(ids_to_keep)
    source_filter = ""
    if source is not None:
        source_filter = " AND source = ?"
        params.append(source)

    cur = conn.execute(
        f"""
        UPDATE listings
        SET is_active = 0
        WHERE id NOT IN ({placeholders}) AND is_active = 1{source_filter}
        """,
        params,
    )
    conn.commit()
    return cur.rowcount
