"""Export the full SQLite database to data/listings_export.json."""
import json
import pathlib
from db.schema import init_db

conn = init_db()
rows = conn.execute("SELECT * FROM listings ORDER BY as24_created_at DESC").fetchall()
data = [dict(r) for r in rows]
out = pathlib.Path("data/listings_export.json")
out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Exported {len(data)} listings -> {out}")
