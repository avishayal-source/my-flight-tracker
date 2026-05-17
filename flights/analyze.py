"""Analyze stored offers — cheapest N-day round trips."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import timedelta

from flights.config import load_config
from flights.db import connect


@dataclass
class RoundTripOption:
    trip_days: int
    outbound_date: str
    return_date: str
    outbound_price: float
    return_price: float
    total_price: float
    outbound_carrier: str
    return_carrier: str
    outbound_flight: str
    return_flight: str
    run_id: int


def _latest_run_id(con) -> int:
    row = con.execute("SELECT MAX(run_id) FROM scrape_runs WHERE status = 'ok'").fetchone()
    if not row or row[0] is None:
        raise SystemExit("No successful scrape runs. Run: python -m flights.ingest --provider mock --once")
    return int(row[0])


def cheapest_roundtrips(
    trip_days_list: list[int],
    run_id: int | None = None,
) -> list[RoundTripOption]:
    cfg = load_config()
    out_dir = f"{cfg.origin}_{cfg.destination}"
    ret_dir = f"{cfg.destination}_{cfg.origin}"
    con = connect()
    try:
        rid = run_id or _latest_run_id(con)
        out_rows = con.execute(
            """
            SELECT departure_date, price_total_usd, carrier_code, flight_number
            FROM offers
            WHERE run_id = ? AND direction = ?
            """,
            [rid, out_dir],
        ).fetchall()
        ret_rows = con.execute(
            """
            SELECT departure_date, price_total_usd, carrier_code, flight_number
            FROM offers
            WHERE run_id = ? AND direction = ?
            """,
            [rid, ret_dir],
        ).fetchall()
    finally:
        con.close()

    returns_by_date = {r[0]: r for r in ret_rows}
    options: list[RoundTripOption] = []

    for trip_days in trip_days_list:
        best: RoundTripOption | None = None
        for o in out_rows:
            out_date, out_price, out_carrier, out_fn = o
            ret_date = out_date + timedelta(days=trip_days)
            r = returns_by_date.get(ret_date)
            if not r:
                continue
            _, ret_price, ret_carrier, ret_fn = r
            total = float(out_price) + float(ret_price)
            cand = RoundTripOption(
                trip_days=trip_days,
                outbound_date=str(out_date),
                return_date=str(ret_date),
                outbound_price=float(out_price),
                return_price=float(ret_price),
                total_price=total,
                outbound_carrier=out_carrier,
                return_carrier=ret_carrier,
                outbound_flight=out_fn,
                return_flight=ret_fn,
                run_id=rid,
            )
            if best is None or cand.total_price < best.total_price:
                best = cand
        if best:
            options.append(best)
    return options


def print_roundtrips(options: list[RoundTripOption]) -> None:
    if not options:
        print("No round-trip pairs found for the given trip lengths.")
        return
    for o in options:
        print(f"\n=== Cheapest {o.trip_days}-day round trip (run {o.run_id}) ===")
        print(f"  Out: {o.outbound_date}  {o.outbound_carrier} {o.outbound_flight}  ${o.outbound_price:.2f}")
        print(f"  Ret: {o.return_date}  {o.return_carrier} {o.return_flight}  ${o.return_price:.2f}")
        print(f"  Total: ${o.total_price:.2f} USD (2 passengers, economy)")


def print_trend(direction: str) -> None:
    con = connect()
    try:
        rows = con.execute(
            """
            SELECT departure_date,
                   MIN(price_total_usd) AS min_price,
                   COUNT(DISTINCT run_id) AS snapshots
            FROM offers
            WHERE direction = ?
            GROUP BY 1
            ORDER BY 1
            """,
            [direction],
        ).fetchall()
    finally:
        con.close()
    print(f"Price by departure date ({direction}):")
    for dep, price, n in rows:
        print(f"  {dep}  min=${price:.2f}  ({n} snapshot(s))")


def main() -> None:
    parser = argparse.ArgumentParser(prog="flights.analyze")
    sub = parser.add_subparsers(dest="cmd", required=True)
    rt = sub.add_parser("roundtrip", help="Cheapest N-day round trip from latest run")
    rt.add_argument("--trip-days", type=int, action="append", required=True)
    rt.add_argument("--run-id", type=int, default=None)
    tr = sub.add_parser("trend", help="Min price per departure date across runs")
    tr.add_argument("--direction", default="TLV_VIE")
    args = parser.parse_args()
    if args.cmd == "roundtrip":
        opts = cheapest_roundtrips(args.trip_days, args.run_id)
        print_roundtrips(opts)
    elif args.cmd == "trend":
        print_trend(args.direction)


if __name__ == "__main__":
    main()
