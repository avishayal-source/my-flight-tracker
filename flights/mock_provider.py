"""Synthetic offers for development without API keys."""
from __future__ import annotations

import hashlib
import random
from datetime import date, datetime, time, timedelta

from flights.config import AppConfig, departure_dates
from flights.models import FlightOffer


def _direction_code(origin: str, dest: str) -> str:
    return f"{origin}_{dest}"


def _stable_seed(*parts: str) -> int:
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(h[:8], 16)


def generate_mock_offers(
    cfg: AppConfig,
    max_days: int | None,
    run_id: int,
    *,
    start_offset_days: int | None = None,
) -> list[FlightOffer]:
    rng = random.Random(run_id)
    offers: list[FlightOffer] = []
    offset = (
        start_offset_days
        if start_offset_days is not None
        else cfg.departure_start_offset_days
    )
    dates = departure_dates(cfg.horizon_days, max_days, offset)

    legs = [
        (_direction_code(cfg.origin, cfg.destination), cfg.origin, cfg.destination, 3, 15),
        (_direction_code(cfg.destination, cfg.origin), cfg.destination, cfg.origin, 4, 18),
    ]

    carriers = ["LY", "OS", "IZ", "UA"]

    for dep_date in dates:
        for direction, _orig, _dest, base_h, dur_h in legs:
            # Stable flight identity across runs (only price changes per scrape).
            identity_rng = random.Random(_stable_seed(direction, dep_date.isoformat()))
            carrier = carriers[identity_rng.randint(0, len(carriers) - 1)]
            flight_num = f"{carrier}{100 + identity_rng.randint(0, 899)}"
            hour = base_h + identity_rng.randint(0, 4)
            minute = [0, 15, 30][identity_rng.randint(0, 2)]
            dep_dt = datetime.combine(dep_date, time(hour=hour, minute=minute))
            arr_dt = dep_dt + timedelta(hours=dur_h, minutes=identity_rng.randint(0, 30))

            price_rng = random.Random(_stable_seed(direction, dep_date.isoformat(), str(run_id)))
            base_price = 180 + (dep_date - date.today()).days * 2.5
            if direction.endswith(f"_{cfg.destination}"):
                base_price += price_rng.uniform(-20, 40)
            else:
                base_price += price_rng.uniform(-10, 30)
            price = round(base_price + price_rng.uniform(-25, 25), 2)

            offers.append(
                FlightOffer(
                    direction=direction,
                    departure_date=dep_date,
                    departure_at=dep_dt,
                    arrival_at=arr_dt,
                    carrier_code=carrier,
                    flight_number=flight_num,
                    duration_minutes=int((arr_dt - dep_dt).total_seconds() // 60),
                    stops=0,
                    price_total_usd=price,
                    adults=cfg.adults,
                    cabin=cfg.cabin,
                    external_id=f"mock-{direction}-{dep_date}-{flight_num}",
                )
            )
    rng.shuffle(offers)
    return offers
