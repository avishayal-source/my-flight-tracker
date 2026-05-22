"""Scheduled alert job: low-price legs + failed ingest notifications."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from flights.db import connect, init_db
from flights.logutil import log_event, setup_logging
from flights.notify import send_email
from flights.timeutil import utc_now

logger = setup_logging()

THRESHOLD_DEFAULT = 250.0
NOTIFY_KEY_INGEST_FAILED = "ingest_failed"


def _threshold() -> float:
    return float(os.getenv("ALERT_THRESHOLD_USD", str(THRESHOLD_DEFAULT)))


def _can_send_ingest_failed(con) -> bool:
    from datetime import datetime, timezone

    row = con.execute(
        "SELECT last_sent_at FROM notification_state WHERE key = ?",
        [NOTIFY_KEY_INGEST_FAILED],
    ).fetchone()
    if not row:
        return True
    last = row[0]
    if not isinstance(last, datetime):
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (utc_now() - last) >= timedelta(hours=24)


def _mark_ingest_failed_sent(con) -> None:
    now = utc_now().replace(tzinfo=None)
    con.execute(
        """
        INSERT INTO notification_state (key, last_sent_at)
        VALUES (?, ?)
        ON CONFLICT (key) DO UPDATE SET last_sent_at = EXCLUDED.last_sent_at
        """,
        [NOTIFY_KEY_INGEST_FAILED, now],
    )


def _latest_ingest(con) -> tuple[int, str, str | None] | None:
    row = con.execute(
        """
        SELECT id, status, error
        FROM ingest_runs
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return None
    return int(row[0]), str(row[1]), row[2]


def _detect_low_price_alerts(con, threshold: float) -> list[int]:
    """Insert new alerts for legs below threshold; return new alert ids."""
    row = con.execute(
        "SELECT MAX(run_id) FROM scrape_runs WHERE status = 'ok'"
    ).fetchone()
    if not row or row[0] is None:
        return []
    run_id = int(row[0])

    legs = con.execute(
        """
        SELECT direction, departure_date, carrier_code, flight_number, price_total_usd
        FROM offers
        WHERE run_id = ? AND price_total_usd < ?
        ORDER BY price_total_usd
        """,
        [run_id, threshold],
    ).fetchall()

    new_ids: list[int] = []
    for direction, dep, carrier, fn, price in legs:
        exists = con.execute(
            """
            SELECT 1 FROM alerts
            WHERE reason = 'leg_below_threshold'
              AND route = ?
              AND flight_date = ?
              AND carrier_code = ?
              AND flight_number = ?
              AND status IN ('new', 'sent')
            LIMIT 1
            """,
            [direction, dep, carrier, fn],
        ).fetchone()
        if exists:
            continue
        ins = con.execute(
            """
            INSERT INTO alerts (
                detected_at, flight_date, return_date, price, reason, status,
                ingest_run_id, route, carrier_code, flight_number
            ) VALUES (NOW(), ?, NULL, ?, 'leg_below_threshold', 'new', ?, ?, ?, ?)
            RETURNING id
            """,
            [dep, float(price), run_id, direction, carrier, fn],
        ).fetchone()
        new_ids.append(int(ins[0]))
    return new_ids


def _format_price_alert(con, alert_id: int) -> str:
    row = con.execute(
        """
        SELECT route, flight_date, carrier_code, flight_number, price
        FROM alerts WHERE id = ?
        """,
        [alert_id],
    ).fetchone()
    if not row:
        return ""
    route, dep, carrier, fn, price = row
    return (
        f"  {route}  {dep}  {carrier} {fn}  ${float(price):.2f} (2 pax, one-way leg)"
    )


def run_alert_job() -> int:
    init_db()
    threshold = _threshold()
    emails_sent = 0

    with connect() as con:
        latest = _latest_ingest(con)
        if latest:
            ingest_id, status, err = latest
            if status == "error" and _can_send_ingest_failed(con):
                body = (
                    f"Ingest run {ingest_id} failed.\n\n"
                    f"Error: {err or 'unknown'}\n\n"
                    f"Check GitHub Actions logs for my-flight-tracker."
                )
                send_email(
                    subject=f"[Flight tracker] Ingest failed (run {ingest_id})",
                    body=body,
                )
                _mark_ingest_failed_sent(con)
                con.execute(
                    """
                    INSERT INTO alerts (detected_at, reason, status, ingest_run_id, price)
                    VALUES (NOW(), 'ingest_failed', 'sent', ?, NULL)
                    """,
                    [ingest_id],
                )
                emails_sent += 1
                log_event(
                    logger,
                    "email_sent",
                    kind="ingest_failed",
                    ingest_run_id=ingest_id,
                )

        new_alert_ids = _detect_low_price_alerts(con, threshold)
        con.commit()

    if new_alert_ids:
        lines = [
            f"TLV-VIE flight tracker: {len(new_alert_ids)} new offer(s) below ${threshold:.0f}",
            "(USD total for 2 passengers on that one-way leg)",
            "",
        ]
        with connect() as con:
            for aid in new_alert_ids:
                lines.append(_format_price_alert(con, aid))
            body = "\n".join(lines)
            send_email(
                subject=f"[Flight tracker] {len(new_alert_ids)} price alert(s) below ${threshold:.0f}",
                body=body,
            )
            for aid in new_alert_ids:
                con.execute(
                    "UPDATE alerts SET status = 'sent' WHERE id = ?",
                    [aid],
                )
            con.commit()
        emails_sent += 1
        log_event(
            logger,
            "email_sent",
            kind="leg_below_threshold",
            count=len(new_alert_ids),
        )

    if not emails_sent:
        log_event(logger, "alert_job_ok", threshold=threshold, new_alerts=0)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run alert + email job")
    parser.parse_args()
    try:
        sys.exit(run_alert_job())
    except Exception as e:
        log_event(logger, "alert_job_error", error=str(e))
        raise


if __name__ == "__main__":
    main()
