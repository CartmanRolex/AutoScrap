# Stub — populate after Phase 1 reveals the API schema
from dataclasses import dataclass
from typing import Optional


@dataclass
class Listing:
    id: str
    url: str
    title: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    mileage_km: Optional[int] = None
    price_chf: Optional[int] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    body_type: Optional[str] = None
    power_hp: Optional[int] = None
    location: Optional[str] = None
    seller_type: Optional[str] = None
    image_url: Optional[str] = None
    raw_json: Optional[str] = None
