"""Parse Anibis search/detail pages into DB-ready listing rows."""
import html
import json
import re

BASE_URL = "https://www.anibis.ch"

_NEXT_DATA_RE = re.compile(
    r"<script[^>]+id=[\"']__NEXT_DATA__[\"'][^>]*>(.*?)</script>",
    re.DOTALL,
)


def _slug(text: str | None) -> str | None:
    if not text:
        return None
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or None


def _parse_int(value: object) -> int | None:
    if value is None:
        return None
    digits = re.sub(r"[^\d]", "", str(value))
    if not digits:
        return None
    return int(digits)


def _safe_sqlite_int(value: object) -> int | None:
    parsed = _parse_int(value)
    if parsed is None or parsed > 9_223_372_036_854_775_807:
        return None
    return parsed


def _extract_next_data(html_text: str) -> dict:
    match = _NEXT_DATA_RE.search(html_text)
    if not match:
        raise ValueError("Anibis page did not contain __NEXT_DATA__")
    return json.loads(html.unescape(match.group(1)))


def _find_query_data(next_data: dict, key: str) -> dict:
    queries = (
        next_data.get("props", {})
        .get("pageProps", {})
        .get("dehydratedState", {})
        .get("queries", [])
    )
    for query in queries:
        data = query.get("state", {}).get("data")
        if isinstance(data, dict) and key in data:
            return data[key]
    raise ValueError(f"Anibis __NEXT_DATA__ did not contain query data for {key!r}")


def extract_search_nodes(html_text: str) -> list[dict]:
    """Return listing nodes from an Anibis search result page."""
    next_data = _extract_next_data(html_text)
    listings = _find_query_data(next_data, "listings")
    return [
        edge["node"]
        for edge in listings.get("edges", [])
        if isinstance(edge, dict) and isinstance(edge.get("node"), dict)
    ]


def extract_detail_listing(html_text: str) -> dict:
    """Return the single listing dict from an Anibis detail page."""
    next_data = _extract_next_data(html_text)
    return _find_query_data(next_data, "listing")


def raw_anibis_id(node: dict) -> str:
    return str(node["listingID"])


def anibis_db_id(node_or_id: dict | str) -> str:
    raw_id = raw_anibis_id(node_or_id) if isinstance(node_or_id, dict) else str(node_or_id)
    return f"anibis:{raw_id}"


def detail_url(node: dict) -> str:
    raw_id = raw_anibis_id(node)
    seo = node.get("seoInformation") or {}
    slug = (seo.get("frSlug") or "").strip("/")
    if slug:
        return f"{BASE_URL}/fr/vi/{slug}/{raw_id}"
    return f"{BASE_URL}/fr/vi/{raw_id}"


def _property_map(detail_node: dict | None) -> dict[str, object]:
    properties = (detail_node or {}).get("properties") or []
    mapped: dict[str, object] = {}
    for prop in properties:
        if not isinstance(prop, dict):
            continue
        key = prop.get("listingPropertyID")
        if not key:
            continue
        mapped[key] = prop.get("text") or prop.get("formattedValue") or prop.get("value")
    return mapped


def _pick(search_node: dict, detail_node: dict | None, key: str) -> object:
    if detail_node and detail_node.get(key) is not None:
        return detail_node.get(key)
    return search_node.get(key)


def parse_anibis_listing(search_node: dict, detail_node: dict | None = None) -> dict:
    """Flatten Anibis search/detail data into the shared listings schema."""
    props = _property_map(detail_node)
    postcode = (_pick(search_node, detail_node, "postcodeInformation") or {}) or {}
    seller = (_pick(search_node, detail_node, "sellerInfo") or {}) or {}
    coordinates = (_pick(search_node, detail_node, "coordinates") or {}) or {}
    primary_category = (_pick(search_node, detail_node, "primaryCategory") or {}) or {}

    make_name = props.get("cars_carAutoScoutBrand")
    model_name = props.get("cars_carAutoScoutModel")
    timestamp = _pick(search_node, detail_node, "timestamp")
    title = _pick(search_node, detail_node, "title")
    body = _pick(search_node, detail_node, "body")

    raw_payload = {"search": search_node, "detail": detail_node}

    return {
        "id": anibis_db_id(search_node),
        "source": "anibis",
        "url": detail_url(search_node),
        "version_full_name": title,
        "condition_type": None,
        "vehicle_category": primary_category.get("categoryID"),
        "body_type": props.get("cars_carAutoScoutBodyType"),
        "color": props.get("cars_carAutoScoutColor"),
        "doors": _parse_int(props.get("cars_carAutoScoutDoors")),
        "make_id": None,
        "make_name": make_name,
        "make_key": _slug(str(make_name)) if make_name else None,
        "model_id": None,
        "model_name": model_name,
        "model_key": _slug(str(model_name)) if model_name else None,
        "horse_power": _parse_int(props.get("cars_carAutoScoutHorsepower")),
        "kilo_watts": None,
        "fuel_type": props.get("cars_carAutoScoutFuelType"),
        "transmission_type": props.get("cars_carAutoScoutTransmissionType"),
        "transmission_type_group": None,
        "mileage": _parse_int(props.get("cars_carAutoScoutMileage")),
        "range_km": None,
        "consumption_combined": None,
        "first_registration_date": None,
        "first_registration_year": _parse_int(
            props.get("cars_carAutoScoutRegistrationYear")
        ),
        "had_accident": None,
        "inspected": None,
        "has_additional_tires": None,
        "has_new_tires": None,
        "price_chf": _parse_int(_pick(search_node, detail_node, "formattedPrice")),
        "previous_price_chf": None,
        "leasing_monthly_chf": None,
        "seller_id": _safe_sqlite_int(seller.get("publicAccountID")),
        "seller_name": seller.get("alias"),
        "seller_type": "professional" if seller.get("subscriptionInfo") else "private",
        "seller_city": postcode.get("locationName"),
        "seller_zip": postcode.get("postcode"),
        "latitude": coordinates.get("latitude"),
        "longitude": coordinates.get("longitude"),
        "warranty_type": None,
        "teaser": body,
        "as24_created_at": timestamp,
        "as24_modified_at": None,
        "raw_json": json.dumps(raw_payload, ensure_ascii=False),
    }
