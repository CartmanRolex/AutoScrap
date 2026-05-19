# Stub — populate after Phase 1 reveals the API schema
import sqlite3
from datetime import datetime, timezone


def upsert_listing(conn: sqlite3.Connection, listing: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO listings (id, url, title, make, model, year, mileage_km,
            price_chf, fuel_type, transmission, body_type, power_hp, location,
            seller_type, image_url, raw_json, first_seen_at, last_seen_at, is_active)
        VALUES (:id, :url, :title, :make, :model, :year, :mileage_km,
            :price_chf, :fuel_type, :transmission, :body_type, :power_hp, :location,
            :seller_type, :image_url, :raw_json, :first_seen_at, :last_seen_at, 1)
        ON CONFLICT(id) DO UPDATE SET
            last_seen_at = excluded.last_seen_at,
            is_active    = 1
        """,
        {**listing, "first_seen_at": now, "last_seen_at": now},
    )
    conn.commit()
