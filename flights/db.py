"""DuckDB persistence for flight offers."""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from flights.config import load_config

SCHEMA = """
CREATE TABLE IF NOT EXISTS scrape_runs (
    run_id BIGINT PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    provider VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    notes VARCHAR
);

CREATE TABLE IF NOT EXISTS offers (
    offer_id BIGINT PRIMARY KEY,
    run_id BIGINT NOT NULL,
    direction VARCHAR NOT NULL,
    departure_date DATE NOT NULL,
    departure_at TIMESTAMP NOT NULL,
    arrival_at TIMESTAMP NOT NULL,
    carrier_code VARCHAR NOT NULL,
    flight_number VARCHAR NOT NULL,
    duration_minutes INTEGER NOT NULL,
    stops INTEGER NOT NULL,
    price_total_usd DOUBLE NOT NULL,
    adults INTEGER NOT NULL,
    cabin VARCHAR NOT NULL,
    fetched_at TIMESTAMP NOT NULL,
    external_id VARCHAR NOT NULL
);
"""


def connect(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    path = db_path or load_config().database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def init_db(db_path: Path | None = None) -> Path:
    path = db_path or load_config().database_path
    con = connect(path)
    try:
        con.execute(SCHEMA)
    finally:
        con.close()
    return path


def next_run_id(con: duckdb.DuckDBPyConnection) -> int:
    row = con.execute("SELECT COALESCE(MAX(run_id), 0) + 1 FROM scrape_runs").fetchone()
    return int(row[0])


def print_stats(db_path: Path | None = None) -> None:
    con = connect(db_path)
    try:
        runs = con.execute("SELECT COUNT(*) FROM scrape_runs").fetchone()[0]
        offers = con.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
        print(f"scrape_runs: {runs}")
        print(f"offers: {offers}")
        if runs:
            print("\nLatest runs:")
            df = con.execute(
                """
                SELECT run_id, provider, status, started_at,
                       (SELECT COUNT(*) FROM offers o WHERE o.run_id = r.run_id) AS n_offers
                FROM scrape_runs r
                ORDER BY run_id DESC
                LIMIT 5
                """
            ).fetchall()
            for row in df:
                print(f"  run {row[0]} | {row[1]} | {row[2]} | {row[3]} | offers={row[4]}")
    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="flights.db")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="Create tables")
    sub.add_parser("stats", help="Print row counts")
    args = parser.parse_args()
    if args.cmd == "init":
        path = init_db()
        print(f"Initialized {path}")
    elif args.cmd == "stats":
        print_stats()


if __name__ == "__main__":
    main()
