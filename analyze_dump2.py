"""Explore the full JSON-LD structure to find where Offer+Car are linked."""
import re
import json
import pathlib

html = pathlib.Path("data/page_dump.html").read_text(encoding="utf-8")
blocks = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL)
data = json.loads(blocks[0])

# Find all objects that have both an Offer and a Car
def find_offers(obj, path="root"):
    results = []
    if isinstance(obj, dict):
        if obj.get("@type") == "Offer" and "itemOffered" in obj:
            results.append((path, obj))
        for k, v in obj.items():
            results.extend(find_offers(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            results.extend(find_offers(item, f"{path}[{i}]"))
    return results

offers = find_offers(data)
print(f"Offer objects with itemOffered: {len(offers)}")
if offers:
    path, first_offer = offers[0]
    print(f"  Path: {path}")
    print(f"  Offer keys: {list(first_offer.keys())}")
    print(f"  itemOffered type: {first_offer['itemOffered'].get('@type')}")
    print(f"  itemOffered keys: {list(first_offer['itemOffered'].keys())}")
    print()
    print("  Full first listing (Offer+Car merged):")
    listing = {
        "price_chf": first_offer.get("price"),
        "currency": first_offer.get("priceCurrency"),
        "url": first_offer.get("url"),
        "availability": first_offer.get("availability"),
        "seller_name": first_offer.get("seller", {}).get("name"),
        "seller_type": first_offer.get("seller", {}).get("@type"),
        "seller_city": first_offer.get("seller", {}).get("address", {}).get("addressLocality"),
        "seller_zip": first_offer.get("seller", {}).get("address", {}).get("postalCode"),
        "car_name": first_offer["itemOffered"].get("name"),
        "car_brand": first_offer["itemOffered"].get("brand", {}).get("name"),
        "car_model": first_offer["itemOffered"].get("model"),
        "car_year": first_offer["itemOffered"].get("modelDate"),
        "car_transmission": first_offer["itemOffered"].get("vehicleTransmission"),
        "car_km": first_offer["itemOffered"].get("mileageFromOdometer", {}).get("value"),
        "car_power_hp": first_offer["itemOffered"].get("vehicleEngine", {}).get("enginePower", {}).get("value"),
        "car_fuel": first_offer["itemOffered"].get("vehicleEngine", {}).get("fuelType"),
        "car_body": first_offer["itemOffered"].get("bodyType"),
        "car_color": first_offer["itemOffered"].get("color"),
        "car_image": first_offer["itemOffered"].get("image"),
    }
    print(json.dumps(listing, indent=2, ensure_ascii=False))

    # Save all merged listings
    all_listings = []
    for _, offer in offers:
        car = offer.get("itemOffered", {})
        all_listings.append({
            "price_chf": offer.get("price"),
            "url": offer.get("url"),
            "seller_name": offer.get("seller", {}).get("name"),
            "seller_type": offer.get("seller", {}).get("@type"),
            "seller_city": offer.get("seller", {}).get("address", {}).get("addressLocality"),
            "car_name": car.get("name"),
            "car_brand": car.get("brand", {}).get("name"),
            "car_model": car.get("model"),
            "car_year": car.get("modelDate"),
            "car_transmission": car.get("vehicleTransmission"),
            "car_km": car.get("mileageFromOdometer", {}).get("value"),
            "car_power_hp": car.get("vehicleEngine", {}).get("enginePower", {}).get("value"),
            "car_fuel": car.get("vehicleEngine", {}).get("fuelType"),
            "car_body": car.get("bodyType"),
            "car_image": car.get("image"),
        })
    out = pathlib.Path("data/all_listings.json")
    out.write_text(json.dumps(all_listings, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved {len(all_listings)} complete listings -> {out}")
