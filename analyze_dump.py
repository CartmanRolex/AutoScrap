"""One-off script to analyze the HTML dump and extract listing structure."""
import re
import json
import pathlib

html = pathlib.Path("data/page_dump.html").read_text(encoding="utf-8")
blocks = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"JSON-LD blocks found: {len(blocks)}")

for i, block in enumerate(blocks):
    try:
        data = json.loads(block)
    except Exception as e:
        print(f"  Block {i}: parse error — {e}")
        continue
    t = data.get("@type", "?")
    keys = list(data.keys())
    print(f"  Block {i}: @type={t}, keys={keys[:10]}")

    # Look for Car / listing arrays inside
    def find_cars(obj, depth=0):
        if isinstance(obj, dict):
            if obj.get("@type") == "Car":
                return [obj]
            cars = []
            for v in obj.values():
                cars.extend(find_cars(v, depth+1))
            return cars
        if isinstance(obj, list):
            cars = []
            for item in obj:
                cars.extend(find_cars(item, depth+1))
            return cars
        return []

    cars = find_cars(data)
    print(f"    Car objects found: {len(cars)}")
    if cars:
        first = cars[0]
        print(f"    First Car keys: {list(first.keys())}")
        print(f"    Sample: {json.dumps(first, ensure_ascii=False, indent=2)[:1000]}")
        # Save all cars
        out = pathlib.Path("data/cars_structured.json")
        out.write_text(json.dumps(cars, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    Saved {len(cars)} cars -> {out}")
