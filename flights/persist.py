"""Write ingest results to Postgres (legacy tables + idempotent leg_observations)."""
from __future__ import annotations

from datetime import datetime

from flights.db import connect
from flights.logutil import log_event, setup_logging
from flights.models import FlightOffer
from flights.timeutil import observed_at_bucket, utc_now

logger = setup_logging()


def start_ingest_run(provider: str) -> tuple[int, datetime]:
    started = utc_now().replace(tzinfo=None)
    with connect() as con:
        row = con.execute(
            """
            INSERT INTO ingest_runs (started_at, status, provider)
            VALUES (?, ?, ?)
            RETURNING id
            """,
            [started, "running", provider],
        ).fetchone()
        ingest_id = int(row[0])
        con.execute(
            """
            INSERT INTO scrape_runs (run_id, started_at, provider, status)
            VALUES (?, ?, ?, 'running')
            """,
            [ingest_id, started, provider],
        )
        con.commit()
    log_event(logger, "ingest_started", ingest_run_id=ingest_id, provider=provider)
    return ingest_id, started


def finish_ingest_run(
    ingest_id: int,
    *,
    status: str,
    records_count: int | None = None,
    error: str | None = None,
) -> None:
    finished = utc_now().replace(tzinfo=None)
    with connect() as con:
        con.execute(
            """
            UPDATE ingest_runs
            SET finished_at = ?, status = ?, records_count = ?, error = ?
            WHERE id = ?
            """,
            [finished, status, records_count, error, ingest_id],
        )
        notes = f"{records_count} offers" if records_count is not None else error
        con.execute(
            """
            UPDATE scrape_runs
            SET completed_at = ?, status = ?, notes = ?
            WHERE run_id = ?
            """,
            [finished, status, notes, ingest_id],
        )
        con.commit()
    log_event(
        logger,
        "ingest_finished",
        ingest_run_id=ingest_id,
        status=status,
        records_count=records_count,
        error=error,
    )


def persist_offers(
    ingest_id: int,
    provider: str,
    offers: list[FlightOffer],
    started: datetime,
) -> int:
    bucket = observed_at_bucket(started)
    with connect() as con:
        for o in offers:
            con.execute(
                """
                INSERT INTO offers (
                    run_id, direction, departure_date, departure_at, arrival_at,
                    carrier_code, flight_number, duration_minutes, stops, price_total_usd,
                    adults, cabin, fetched_at, external_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    ingest_id,
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
            con.execute(
                """
                INSERT INTO leg_observations (
                    ingest_run_id, route, outbound_date, return_date, provider,
                    observed_at_bucket, direction, departure_at, arrival_at,
                    carrier_code, flight_number, duration_minutes, stops,
                    price_total_usd, adults, cabin, external_id
                ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (route, outbound_date, return_date, provider, observed_at_bucket)
                DO UPDATE SET
                    ingest_run_id = EXCLUDED.ingest_run_id,
                    direction = EXCLUDED.direction,
                    departure_at = EXCLUDED.departure_at,
                    arrival_at = EXCLUDED.arrival_at,
                    carrier_code = EXCLUDED.carrier_code,
                    flight_number = EXCLUDED.flight_number,
                    duration_minutes = EXCLUDED.duration_minutes,
                    stops = EXCLUDED.stops,
                    price_total_usd = EXCLUDED.price_total_usd,
                    adults = EXCLUDED.adults,
                    cabin = EXCLUDED.cabin,
                    external_id = EXCLUDED.external_id
                """,
                [
                    ingest_id,
                    o.direction,
                    o.departure_date,
                    provider,
                    bucket,
                    o.direction,
                    o.departure_at,
                    o.arrival_at,
                    o.carrier_code,
                    o.flight_number,
                    o.duration_minutes,
                    o.stops,
                    o.price_total_usd,
                    o.adults,
                    o.cabin,
                    o.external_id,
                ],
            )
        con.commit()
    log_event(
        logger,
        "ingest_persisted",
        ingest_run_id=ingest_id,
        offers=len(offers),
        observed_at_bucket=bucket.isoformat(),
    )
    return len(offers)
