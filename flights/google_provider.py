"""Google Flights — Playwright ingest (real prices)."""
from __future__ import annotations

import os

from flights.config import AppConfig
from flights.google_playwright import GooglePlaywrightError, fetch_google_playwright_offers
from flights.models import FlightOffer


def fetch_google_offers(
    cfg: AppConfig,
    max_days: int | None,
    run_id: int,
    *,
    start_offset_days: int | None = None,
    pause_seconds: float = 3.0,
) -> list[FlightOffer]:
    headless = os.getenv("GOOGLE_HEADLESS", "true").lower() not in ("0", "false", "no")
    pause = float(os.getenv("GOOGLE_FETCH_PAUSE_SECONDS", str(pause_seconds)))
    return fetch_google_playwright_offers(
        cfg,
        max_days,
        run_id,
        start_offset_days=start_offset_days,
        headless=headless,
        pause_seconds=pause,
    )


__all__ = ["fetch_google_offers", "GooglePlaywrightError"]
