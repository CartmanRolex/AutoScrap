"""Quick smoke test: parse existing page_dump.html and print extracted listings."""
import pathlib
import json
from scraper.fetcher import extract_listings_from_html
from scraper.parser import parse_listing
from db.schema import init_db
from db.repository import upsert_listing, count_listings

html = pathlib.Path("data/page_dump.html").read_text(encoding="utf-8")
raw = extract_listings_from_html(html)
print(f"Extracted {len(raw)} raw listings")

if not raw:
    print("ERROR: no listings extracted")
    exit(1)

conn = init_db()
for r in raw:
    upsert_listing(conn, parse_listing(r))

print(f"DB now has {count_listings(conn)} listings")
print()

# Show first 3
cur = conn.execute(
    "SELECT id, make_name, model_name, version_full_name, price_chf, mileage, "
    "fuel_type, condition_type, seller_city, as24_created_at FROM listings LIMIT 3"
)
for row in cur:
    print(dict(row))
