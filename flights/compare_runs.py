"""Compare prices across scrape runs — same flight and days-to-departure trends."""
from __future__ import annotations

from datetime import date

from flights.db import connect


def compare_runs_summary(direction: str | None = None) -> str:
    """How often prices changed between runs (per date+direction, and per exact flight)."""
    con = connect()
    try:
        dir_filter = "WHERE direction = ?" if direction else ""
        params = [direction] if direction else []

        row = con.execute(
            f"""
            SELECT
                COUNT(*) AS pairs,
                SUM(CASE WHEN distinct_prices > 1 THEN 1 ELSE 0 END) AS changed
            FROM (
                SELECT direction, departure_date,
                       COUNT(DISTINCT price_total_usd) AS distinct_prices
                FROM offers {dir_filter}
                GROUP BY 1, 2
                HAVING COUNT(DISTINCT run_id) > 1
            ) t
            """,
            params,
        ).fetchone()

        flight_row = con.execute(
            f"""
            SELECT
                COUNT(*) AS flights,
                SUM(CASE WHEN distinct_prices > 1 THEN 1 ELSE 0 END) AS changed
            FROM (
                SELECT direction, departure_date, carrier_code, flight_number,
                       COUNT(DISTINCT price_total_usd) AS distinct_prices
                FROM offers {dir_filter}
                GROUP BY 1, 2, 3, 4
                HAVING COUNT(DISTINCT run_id) > 1
            ) t
            """,
            params,
        ).fetchone()

        runs = con.execute("SELECT COUNT(*) FROM scrape_runs WHERE status = 'ok'").fetchone()[0]
    finally:
        con.close()

    pairs, changed_dates = int(row[0] or 0), int(row[1] or 0)
    flights, changed_flights = int(flight_row[0] or 0), int(flight_row[1] or 0)

    label = direction or "all directions"
    lines = [
        f"Compare runs summary ({label}, {runs} successful scrape runs):",
        f"  Cheapest-by-date: {changed_dates} / {pairs} departure dates changed price across runs",
        f"  Same flight (carrier+number+date): {changed_flights} / {flights} flights changed price across runs",
        "",
        "For one departure date over time: departure_date_price_over_runs(direction, date).",
        "For one flight identity: same_flight_price_over_runs(...).",
        "For booking window curve: price_vs_days_to_departure(direction).",
    ]
    return "\n".join(lines)


def same_flight_price_over_runs(
    direction: str,
    departure_date: str,
    carrier_code: str,
    flight_number: str,
) -> str:
    """Price of one flight (same carrier+number+date) across each scrape run."""
    con = connect()
    try:
        rows = con.execute(
            """
            SELECT o.run_id, r.started_at, o.price_total_usd,
                   o.departure_at, o.fetched_at
            FROM offers o
            JOIN scrape_runs r ON r.run_id = o.run_id
            WHERE o.direction = ?
              AND o.departure_date = ?::DATE
              AND o.carrier_code = ?
              AND o.flight_number = ?
            ORDER BY r.started_at
            """,
            [direction, departure_date, carrier_code, flight_number],
        ).fetchall()
    finally:
        con.close()

    if not rows:
        return (
            f"No rows for {direction} {departure_date} {carrier_code} {flight_number}. "
            "Try departure_date_price_over_runs if mock data uses different flight numbers each run."
        )

    prices = [float(r[2]) for r in rows]
    lines = [
        f"Same flight over runs: {direction} {departure_date} {carrier_code} {flight_number}",
        f"  Observations: {len(rows)}  min=${min(prices):.2f}  max=${max(prices):.2f}  "
        f"spread=${max(prices) - min(prices):.2f}",
        "",
    ]
    for run_id, started, price, dep_at, fetched in rows:
        days_out = (date.fromisoformat(departure_date) - started.date()).days
        lines.append(
            f"  run {run_id}  scraped {started}  ({days_out}d before departure)  "
            f"${price:.2f}  dep {dep_at}"
        )

    if len(prices) >= 2:
        first, last = prices[0], prices[-1]
        trend = "down" if last < first else "up" if last > first else "flat"
        lines.append(f"\n  Wall-clock trend (first run -> last run): {trend} (${first:.2f} -> ${last:.2f})")

    return "\n".join(lines)


def departure_date_price_over_runs(direction: str, departure_date: str) -> str:
    """Cheapest offer for a departure date on each scrape run (when flight identity shifts)."""
    con = connect()
    try:
        rows = con.execute(
            """
            SELECT o.run_id, r.started_at,
                   MIN(o.price_total_usd) AS price,
                   arg_min(o.carrier_code, o.price_total_usd) AS carrier,
                   arg_min(o.flight_number, o.price_total_usd) AS flight
            FROM offers o
            JOIN scrape_runs r ON r.run_id = o.run_id
            WHERE o.direction = ? AND o.departure_date = ?::DATE
            GROUP BY o.run_id, r.started_at
            ORDER BY r.started_at
            """,
            [direction, departure_date],
        ).fetchall()
    finally:
        con.close()

    if not rows:
        return f"No offers for {direction} on {departure_date}."

    prices = [float(r[2]) for r in rows]
    lines = [
        f"Cheapest {direction} on {departure_date} per scrape run:",
        f"  {len(rows)} runs  min=${min(prices):.2f}  max=${max(prices):.2f}  spread=${max(prices)-min(prices):.2f}",
        "",
    ]
    for run_id, started, price, carrier, flight in rows:
        days_out = (date.fromisoformat(departure_date) - started.date()).days
        lines.append(
            f"  run {run_id}  scraped {started}  ({days_out}d before dep)  "
            f"${price:.2f}  {carrier} {flight}"
        )
    return "\n".join(lines)


def price_vs_days_to_departure(
    direction: str = "TLV_VIE",
    use_latest_run_only: bool = False,
) -> str:
    """
  How price relates to booking window (days from scrape time to departure).

  Pooled across all runs unless use_latest_run_only=True.
  Answers: 'Do nearer departures cost more/less in our snapshots?'
    """
    con = connect()
    try:
        run_clause = ""
        if use_latest_run_only:
            run_clause = "AND run_id = (SELECT MAX(run_id) FROM scrape_runs WHERE status = 'ok')"

        rows = con.execute(
            f"""
            SELECT
                DATE_DIFF('day', CAST(o.fetched_at AS DATE), o.departure_date) AS days_to_departure,
                MIN(o.price_total_usd) AS min_price,
                AVG(o.price_total_usd) AS avg_price,
                COUNT(*) AS n_offers
            FROM offers o
            WHERE o.direction = ?
              AND DATE_DIFF('day', CAST(o.fetched_at AS DATE), o.departure_date) >= 0
              {run_clause}
            GROUP BY 1
            ORDER BY 1 DESC
            """,
            [direction],
        ).fetchall()
    finally:
        con.close()

    if not rows:
        return f"No data for {direction}."

    lines = [
        f"Price vs days to departure ({direction}, "
        f"{'latest run only' if use_latest_run_only else 'all runs pooled'}):",
        "  days_to_departure = departure_date - scrape_date",
        "",
    ]
    for days, min_p, avg_p, n in rows:
        lines.append(f"  {days:3d} days out  min=${min_p:.2f}  avg=${avg_p:.2f}  (n={n})")

    if len(rows) >= 2:
        near = rows[-1]  # smallest days out
        far = rows[0]  # largest days out
        lines.append(
            f"\n  Far window ({far[0]}d): min=${far[1]:.2f}  |  "
            f"Near window ({near[0]}d): min=${near[1]:.2f}"
        )
    return "\n".join(lines)
