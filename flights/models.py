from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class FlightOffer:
    direction: str  # TLV_VIE | VIE_TLV
    departure_date: date
    departure_at: datetime
    arrival_at: datetime
    carrier_code: str
    flight_number: str
    duration_minutes: int
    stops: int
    price_total_usd: float
    adults: int
    cabin: str
    external_id: str
