"""Price alerts — deterministic checks on DuckDB."""
from __future__ import annotations

from flights.db import connect


def offers_below_price(threshold_usd: float, run_id: int | None = None) -> str:
    """
    All one-way offers in a scrape run cheaper than threshold (USD total for 2 pax on that leg).
    """
    con = connect()
    try:
        if run_id is None:
            row = con.execute(
                "SELECT MAX(run_id) FROM scrape_runs WHERE status = 'ok'"
            ).fetchone()
            if not row or row[0] is None:
                return "No scrape runs in the database."
            rid = int(row[0])
        else:
            rid = int(run_id)

        rows = con.execute(
            """
            SELECT direction, departure_date, carrier_code, flight_number, price_total_usd
            FROM offers
            WHERE run_id = ? AND price_total_usd < ?
            ORDER BY price_total_usd
            """,
            [rid, threshold_usd],
        ).fetchall()
    finally:
        con.close()

    if not rows:
        return (
            f"[OK] No offers below ${threshold_usd:.0f} in run {rid} "
            f"(price = total USD for 2 passengers on that one-way leg)."
        )

    lines = [
        f"[ALERT] {len(rows)} offer(s) below ${threshold_usd:.0f} in run {rid}:",
    ]
    for direction, dep, carrier, fn, price in rows:
        lines.append(f"  {direction}  {dep}  {carrier} {fn}  ${price:.2f}")
    return "\n".join(lines)


def offers_below_price_latest_across_runs(threshold_usd: float, last_n_runs: int = 3) -> str:
    """Scan last N scrape runs for any offer under threshold."""
    con = connect()
    try:
        runs = con.execute(
            """
            SELECT run_id FROM scrape_runs WHERE status = 'ok'
            ORDER BY run_id DESC LIMIT ?
            """,
            [last_n_runs],
        ).fetchall()
        if not runs:
            return "No scrape runs."
        rids = [int(r[0]) for r in runs]
        lines: list[str] = [
            f"Scan: last {len(rids)} run(s) — below ${threshold_usd:.0f}:",
        ]
        any_hit = False
        for rid in rids:
            sub = con.execute(
                """
                SELECT direction, departure_date, carrier_code, flight_number, price_total_usd
                FROM offers WHERE run_id = ? AND price_total_usd < ?
                ORDER BY price_total_usd LIMIT 20
                """,
                [rid, threshold_usd],
            ).fetchall()
            if sub:
                any_hit = True
                lines.append(f"\nrun_id={rid}:")
                for row in sub:
                    lines.append(
                        f"  {row[0]} {row[1]} {row[2]} {row[3]} ${row[4]:.2f}"
                    )
        if not any_hit:
            lines.insert(
                0,
                f"[OK] None of the last {len(rids)} run(s) had a leg below ${threshold_usd:.0f}.",
            )
        else:
            lines.insert(
                0,
                f"[ALERT] At least one leg below ${threshold_usd:.0f} in the last {len(rids)} run(s).",
            )
    finally:
        con.close()
    return "\n".join(lines)
