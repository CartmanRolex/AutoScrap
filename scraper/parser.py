"""Parse raw listing dicts from AutoScout24 into clean DB-ready rows."""
import json
import re


def _slug(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')


def _as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _name_from(value):
    if isinstance(value, dict):
        return value.get("name")
    if isinstance(value, str):
        return value
    return None


def parse_listing(raw: dict) -> dict:
    """Flatten a raw listing dict into a single-level dict ready for DB insert."""
    listing_id = str(raw["id"])
    version = raw.get("versionFullName") or ""
    make = raw.get("make")
    model = raw.get("model")
    make_dict = _as_dict(make)
    model_dict = _as_dict(model)
    make_key = make_dict.get("key") or (_slug(make) if isinstance(make, str) else "")

    # Construct the canonical listing URL
    if version and make_key:
        url = f"https://www.autoscout24.ch/fr/d/{_slug(version)}-{listing_id}"
    else:
        url = f"https://www.autoscout24.ch/fr/d/{listing_id}"

    seller = _as_dict(raw.get("seller"))
    leasing = _as_dict(raw.get("leasing"))
    warranty = _as_dict(raw.get("warranty"))
    consumption = _as_dict(raw.get("consumption"))

    return {
        "id": listing_id,
        "source": "autoscout24",
        "canonical_id": listing_id,
        "external_source": None,
        "external_id": None,
        "external_url": None,
        "url": url,
        "version_full_name": version,
        "condition_type": raw.get("conditionType"),
        "vehicle_category": raw.get("vehicleCategory"),
        # Make / model
        "make_id": make_dict.get("id"),
        "make_name": _name_from(make),
        "make_key": make_key,
        "model_id": model_dict.get("id"),
        "model_name": _name_from(model),
        "model_key": model_dict.get("key") or (_slug(model) if isinstance(model, str) else None),
        # Performance & specs
        "horse_power": raw.get("horsePower"),
        "kilo_watts": raw.get("kiloWatts"),
        "fuel_type": raw.get("fuelType"),
        "transmission_type": raw.get("transmissionType"),
        "transmission_type_group": raw.get("transmissionTypeGroup"),
        "mileage": raw.get("mileage"),
        "range_km": raw.get("range"),
        "consumption_combined": consumption.get("combined"),
        # Registration & history
        "first_registration_date": raw.get("firstRegistrationDate"),
        "first_registration_year": raw.get("firstRegistrationYear"),
        "had_accident": raw.get("hadAccident"),
        "inspected": raw.get("inspected"),
        "has_additional_tires": raw.get("hasAdditionalSetOfTires"),
        "has_new_tires": raw.get("hasNewTires"),
        # Price
        "price_chf": raw.get("price"),
        "previous_price_chf": raw.get("previousPrice"),
        "leasing_monthly_chf": leasing.get("monthlyRate"),
        # Seller
        "seller_id": seller.get("id"),
        "seller_name": seller.get("name"),
        "seller_type": seller.get("type"),
        "seller_city": seller.get("city"),
        "seller_zip": seller.get("zipCode"),
        # Warranty
        "warranty_type": warranty.get("type"),
        # Description
        "teaser": raw.get("teaser"),
        # Timestamps from AutoScout24
        "as24_created_at": raw.get("createdDate"),
        "as24_modified_at": raw.get("lastModifiedDate"),
        # Full raw JSON for forward-compatibility
        "raw_json": json.dumps(raw, ensure_ascii=False),
    }
