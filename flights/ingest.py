"""Fetch flight offers and store snapshots."""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from flights.config import load_config, departure_dates
from flights.db import connect, init_db, next_run_id
from flights.google_playwright import GooglePlaywrightError
from flights.google_provider import fetch_google_offers

GoogleFlightsError = GooglePlaywrightError
from flights.mock_provider import generate_mock_offers
from flights.models import FlightOffer


def _persist(run_id: int, provider: str, offers: list[FlightOffer], db_path) -> int:
    con = connect(db_path)
    started = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        con.execute(
            """
            INSERT INTO scrape_runs (run_id, started_at, provider, status)
            VALUES (?, ?, ?, 'running')
            """,
            [run_id, started, provider],
        )
        base = con.execute("SELECT COALESCE(MAX(offer_id), 0) FROM offers").fetchone()[0]
        for i, o in enumerate(offers, start=1):
            con.execute(
                """
                INSERT INTO offers (
                    offer_id, run_id, direction, departure_date, departure_at, arrival_at,
                    carrier_code, flight_number, duration_minutes, stops, price_total_usd,
                    adults, cabin, fetched_at, external_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    base + i,
                    run_id,
                    o.direction,
                    o.departure_date,
                    o.departure_at,
                    o.arrival_at,
                    o.carrier_code,
                    o.flight_number,
                    o.duration_minutes,
                    o.stops,
                    o.price_total_usd,
                    o.adults,
                    o.cabin,
                    started,
                    o.external_id,
                ],
            )
        completed = datetime.now(timezone.utc).replace(tzinfo=None)
        con.execute(
            """
            UPDATE scrape_runs
            SET completed_at = ?, status = 'ok', notes = ?
            WHERE run_id = ?
            """,
            [completed, f"{len(offers)} offers", run_id],
        )
    except Exception:
        con.execute(
            "UPDATE scrape_runs SET status = 'error' WHERE run_id = ?",
            [run_id],
        )
        raise
    finally:
        con.close()
    return len(offers)


def run_once(
    provider: str,
    max_days: int | None,
    headful: bool = False,
    start_offset_days: int | None = None,
) -> None:
    cfg = load_config()
    init_db(cfg.database_path)
    con = connect(cfg.database_path)
    run_id = next_run_id(con)
    con.close()

    offset = (
        start_offset_days
        if start_offset_days is not None
        else cfg.departure_start_offset_days
    )
    dates = departure_dates(cfg.horizon_days, max_days, offset)
    print(
        f"Run {run_id} | provider={provider} | "
        f"departures={len(dates)} from offset={offset} "
        f"({dates[0] if dates else 'none'} … {dates[-1] if dates else 'none'})"
    )

    if provider == "mock":
        offers = generate_mock_offers(cfg, max_days, run_id, start_offset_days=start_offset_days)
    elif provider == "google":
        if headful:
            import os

            os.environ["GOOGLE_HEADLESS"] = "false"
        offers = fetch_google_offers(
            cfg, max_days, run_id, start_offset_days=start_offset_days
        )
    else:
        raise SystemExit(f"Unknown provider: {provider}. Use mock or google.")

    n = _persist(run_id, provider, offers, cfg.database_path)
    print(f"Stored {n} offers in {cfg.database_path}")


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
    interval = args.interval_seconds if args.interval_seconds is not None else cfg.interval_seconds

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
