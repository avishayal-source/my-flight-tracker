"""Fetch flight offers and store snapshots in Postgres."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from flights.config import load_config, departure_dates
from flights.db import init_db
from flights.google_playwright import GooglePlaywrightError
from flights.google_provider import fetch_google_offers
from flights.logutil import log_event, setup_logging
from flights.mock_provider import generate_mock_offers
from flights.persist import finish_ingest_run, persist_offers, start_ingest_run

GoogleFlightsError = GooglePlaywrightError

logger = setup_logging()


def run_once(
    provider: str,
    max_days: int | None,
    headful: bool = False,
    start_offset_days: int | None = None,
) -> None:
    cfg = load_config()
    init_db()

    offset = (
        start_offset_days
        if start_offset_days is not None
        else cfg.departure_start_offset_days
    )
    dates = departure_dates(cfg.horizon_days, max_days, offset)

    ingest_id, started = start_ingest_run(provider)
    print(
        f"Ingest {ingest_id} | provider={provider} | "
        f"departures={len(dates)} from offset={offset} "
        f"({dates[0] if dates else 'none'} … {dates[-1] if dates else 'none'})"
    )

    try:
        if provider == "mock":
            offers = generate_mock_offers(
                cfg, max_days, ingest_id, start_offset_days=start_offset_days
            )
        elif provider == "google":
            if headful:
                import os

                os.environ["GOOGLE_HEADLESS"] = "false"
            offers = fetch_google_offers(
                cfg, max_days, ingest_id, start_offset_days=start_offset_days
            )
        else:
            raise SystemExit(f"Unknown provider: {provider}. Use mock or google.")

        n = persist_offers(ingest_id, provider, offers, started)
        finish_ingest_run(ingest_id, status="ok", records_count=n)
        print(f"Stored {n} offers (ingest_run_id={ingest_id})")
        log_event(logger, "ingest_ok", ingest_run_id=ingest_id, offers=n)
    except Exception as e:
        finish_ingest_run(ingest_id, status="error", error=str(e))
        log_event(logger, "ingest_error", ingest_run_id=ingest_id, error=str(e))
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest TLV-VIE flight offers")
    parser.add_argument(
        "--provider",
        choices=("mock", "google"),
        default="google",
        help="google = Google Flights (Playwright); mock = offline only",
    )
    parser.add_argument("--once", action="store_true", help="Single run then exit")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=None,
        help="Loop interval (overrides config.yaml)",
    )
    parser.add_argument(
        "--max-days",
        type=int,
        default=None,
        help="Limit departure dates (recommended for google: 3-7)",
    )
    parser.add_argument(
        "--start-offset-days",
        type=int,
        default=None,
        help="First departure = today + N (default: config search.departure_start_offset_days)",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Show browser window (debug Google scraping)",
    )
    args = parser.parse_args()
    cfg = load_config()
    interval = (
        args.interval_seconds if args.interval_seconds is not None else cfg.interval_seconds
    )

    def _run() -> None:
        try:
            run_once(args.provider, args.max_days, args.headful, args.start_offset_days)
        except GoogleFlightsError as e:
            print(f"Google Flights error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.once or args.interval_seconds is None:
        _run()
        return

    print(f"Polling every {interval}s (Ctrl+C to stop)")
    while True:
        try:
            _run()
        except GoogleFlightsError as e:
            print(f"Google Flights error: {e}", file=sys.stderr)
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        time.sleep(interval)


if __name__ == "__main__":
    main()
