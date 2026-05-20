import sqlite3
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_listing(conn: sqlite3.Connection, listing: dict) -> bool:
    """Insert a new listing or update last_seen_at on duplicate. Returns True if new."""
    now = _now()
    try:
        conn.execute(
            """
            INSERT INTO listings (
                id, url, version_full_name, condition_type, vehicle_category,
                make_id, make_name, make_key, model_id, model_name, model_key,
                horse_power, kilo_watts, fuel_type, transmission_type,
                transmission_type_group, mileage, range_km, consumption_combined,
                first_registration_date, first_registration_year,
                had_accident, inspected, has_additional_tires, has_new_tires,
                price_chf, previous_price_chf, leasing_monthly_chf,
                seller_id, seller_name, seller_type, seller_city, seller_zip,
                warranty_type, teaser, as24_created_at, as24_modified_at,
                first_seen_at, last_seen_at, is_active, raw_json
            ) VALUES (
                :id, :url, :version_full_name, :condition_type, :vehicle_category,
                :make_id, :make_name, :make_key, :model_id, :model_name, :model_key,
                :horse_power, :kilo_watts, :fuel_type, :transmission_type,
                :transmission_type_group, :mileage, :range_km, :consumption_combined,
                :first_registration_date, :first_registration_year,
                :had_accident, :inspected, :has_additional_tires, :has_new_tires,
                :price_chf, :previous_price_chf, :leasing_monthly_chf,
                :seller_id, :seller_name, :seller_type, :seller_city, :seller_zip,
                :warranty_type, :teaser, :as24_created_at, :as24_modified_at,
                :first_seen_at, :last_seen_at, 1, :raw_json
            )
            ON CONFLICT(id) DO UPDATE SET
                last_seen_at     = excluded.last_seen_at,
                as24_modified_at = excluded.as24_modified_at,
                price_chf        = excluded.price_chf,
                previous_price_chf = excluded.previous_price_chf,
                is_active        = 1,
                raw_json         = excluded.raw_json
            """,
            {**listing, "first_seen_at": now, "last_seen_at": now},
        )
        conn.commit()
        # rowcount == 1 for INSERT, but we can't distinguish insert from update here.
        # Check changes: if last_insert_rowid changed, it was an insert.
        return conn.execute("SELECT changes()").fetchone()[0] > 0
    except sqlite3.Error as e:
        conn.rollback()
        raise


def count_listings(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]


def mark_inactive(conn: sqlite3.Connection, ids_to_keep: list[str]) -> int:
    """Mark all listings not in ids_to_keep as inactive (no longer in results)."""
    if not ids_to_keep:
        return 0
    placeholders = ",".join("?" * len(ids_to_keep))
    cur = conn.execute(
        f"UPDATE listings SET is_active = 0 WHERE id NOT IN ({placeholders}) AND is_active = 1",
        ids_to_keep,
    )
    conn.commit()
    return cur.rowcount
