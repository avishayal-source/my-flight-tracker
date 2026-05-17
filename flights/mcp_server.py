"""MCP server — expose flight DB tools to Cursor and other MCP hosts."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from flights.analyze import cheapest_roundtrips
from flights import compare_runs as compare_mod
from flights.db import connect, print_stats

mcp = FastMCP(
    "flights-tracker",
    instructions=(
        "Read-only tools over a local TLV-VIE flight price database. "
        "Use cheapest_roundtrip for trip planning; price_trend for min price by departure date; "
        "compare_runs_summary / same_flight_price_over_runs for price changes across scrape runs; "
        "price_vs_days_to_departure for booking-window trends (days until departure). "
        "offers_below_price for alerts when leg price drops below a USD threshold. "
        "Prices are USD totals for 2 economy passengers unless noted."
    ),
)


@mcp.tool()
def db_stats() -> str:
    """Row counts and the five most recent ingest runs."""
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        print_stats()
    return buf.getvalue()


@mcp.tool()
def cheapest_roundtrip(trip_days: int = 4, run_id: int | None = None) -> str:
    """Cheapest round trip for N days (outbound + return, any airline combo)."""
    opts = cheapest_roundtrips([trip_days], run_id=run_id)
    if not opts:
        return f"No {trip_days}-day round trip found for run_id={run_id or 'latest'}."
    o = opts[0]
    return (
        f"Cheapest {o.trip_days}-day round trip (run {o.run_id}):\n"
        f"  Out: {o.outbound_date}  {o.outbound_carrier} {o.outbound_flight}  ${o.outbound_price:.2f}\n"
        f"  Ret: {o.return_date}  {o.return_carrier} {o.return_flight}  ${o.return_price:.2f}\n"
        f"  Total: ${o.total_price:.2f} USD (2 passengers, economy)"
    )


@mcp.tool()
def price_trend(direction: str = "TLV_VIE", limit: int = 15) -> str:
    """Minimum price per departure date across all snapshots (TLV_VIE or VIE_TLV)."""
    if direction not in ("TLV_VIE", "VIE_TLV"):
        return "direction must be TLV_VIE or VIE_TLV"
    con = connect()
    try:
        rows = con.execute(
            """
            SELECT departure_date, MIN(price_total_usd) AS min_price,
                   COUNT(DISTINCT run_id) AS snapshots
            FROM offers
            WHERE direction = ?
            GROUP BY 1
            ORDER BY 1
            LIMIT ?
            """,
            [direction, limit],
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return f"No offers for direction {direction}."
    lines = [f"Price trend ({direction}):"]
    for dep, price, n in rows:
        lines.append(f"  {dep}  min=${price:.2f}  ({n} snapshot(s))")
    return "\n".join(lines)


@mcp.tool()
def list_offers(
    direction: str = "TLV_VIE",
    departure_date: str | None = None,
    run_id: int | None = None,
    limit: int = 10,
) -> str:
    """List stored offers for a direction; optional filter by YYYY-MM-DD date."""
    con = connect()
    try:
        rid = run_id
        if rid is None:
            row = con.execute(
                "SELECT MAX(run_id) FROM scrape_runs WHERE status = 'ok'"
            ).fetchone()
            rid = int(row[0]) if row and row[0] is not None else None
        if rid is None:
            return "No scrape runs in database."
        sql = """
            SELECT departure_date, carrier_code, flight_number, price_total_usd
            FROM offers
            WHERE run_id = ? AND direction = ?
        """
        params: list = [rid, direction]
        if departure_date:
            sql += " AND departure_date = ?::DATE"
            params.append(departure_date)
        sql += " ORDER BY price_total_usd LIMIT ?"
        params.append(limit)
        rows = con.execute(sql, params).fetchall()
    finally:
        con.close()
    if not rows:
        return "No matching offers."
    lines = [f"Offers run_id={rid} direction={direction}:"]
    for dep, carrier, fn, price in rows:
        lines.append(f"  {dep}  {carrier} {fn}  ${price:.2f}")
    return "\n".join(lines)


@mcp.tool()
def compare_runs(direction: str | None = None) -> str:
    """Summary: how many dates/flights changed price across scrape runs. direction: TLV_VIE, VIE_TLV, or omit for all."""
    if direction and direction not in ("TLV_VIE", "VIE_TLV"):
        return "direction must be TLV_VIE, VIE_TLV, or omitted"
    return compare_mod.compare_runs_summary(direction)


@mcp.tool()
def same_flight_price_over_runs(
    direction: str,
    departure_date: str,
    carrier_code: str,
    flight_number: str,
) -> str:
    """Track one flight's price across scrape runs (same carrier, flight number, departure date)."""
    if direction not in ("TLV_VIE", "VIE_TLV"):
        return "direction must be TLV_VIE or VIE_TLV"
    return compare_mod.same_flight_price_over_runs(
        direction, departure_date, carrier_code, flight_number
    )


@mcp.tool()
def departure_date_price_over_runs(direction: str, departure_date: str) -> str:
    """Cheapest offer for a departure date on each scrape run (use when flight number changes between runs)."""
    if direction not in ("TLV_VIE", "VIE_TLV"):
        return "direction must be TLV_VIE or VIE_TLV"
    return compare_mod.departure_date_price_over_runs(direction, departure_date)


@mcp.tool()
def price_vs_days_to_departure(
    direction: str = "TLV_VIE",
    use_latest_run_only: bool = False,
) -> str:
    """Trend: min/avg price by days from scrape date to departure (booking window)."""
    if direction not in ("TLV_VIE", "VIE_TLV"):
        return "direction must be TLV_VIE or VIE_TLV"
    return compare_mod.price_vs_days_to_departure(direction, use_latest_run_only)


@mcp.tool()
def offers_below_price(threshold_usd: float = 250.0, run_id: int | None = None) -> str:
    """List offers in latest (or given) scrape run cheaper than threshold_usd (per leg, 2 pax)."""
    from flights.alerts import offers_below_price as _below

    return _below(threshold_usd, run_id)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
