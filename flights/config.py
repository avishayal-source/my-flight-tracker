from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AppConfig:
    origin: str
    destination: str
    horizon_days: int
    # First departure day = today + this (0 = today).
    departure_start_offset_days: int
    direct_only: bool
    adults: int
    cabin: str
    currency: str
    interval_seconds: int
    database_path: Path


def load_config(path: Path | None = None) -> AppConfig:
    cfg_path = path or ROOT / "config.yaml"
    if not cfg_path.exists():
        cfg_path = ROOT / "config.example.yaml"
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    search = raw["search"]
    return AppConfig(
        origin=raw["route"]["origin"],
        destination=raw["route"]["destination"],
        horizon_days=int(search["horizon_days"]),
        departure_start_offset_days=int(search.get("departure_start_offset_days", 0)),
        direct_only=bool(search["direct_only"]),
        adults=int(search["adults"]),
        cabin=search["cabin"],
        currency=search["currency"],
        interval_seconds=int(raw["ingest"]["interval_seconds"]),
        database_path=ROOT / raw["database"]["path"],
    )


def departure_dates(
    horizon_days: int,
    max_days: int | None = None,
    start_offset_days: int = 0,
) -> list:
    """Departure calendar days to query.

    - start_offset_days=0, max_days=3 → today, today+1, today+2 (capped by horizon).
    - start_offset_days=3, max_days=3 → today+3, today+4, today+5.
    """
    from datetime import date, timedelta

    today = date.today()
    if start_offset_days > 0:
        max_span = max(0, horizon_days - start_offset_days)
        span = min(max_span, max_days) if max_days is not None else max_span
        return [today + timedelta(days=start_offset_days + i) for i in range(span)]

    if max_days is not None:
        n = min(horizon_days, max_days)
    else:
        n = horizon_days
    return [today + timedelta(days=i) for i in range(n)]
