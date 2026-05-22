"""Postgres persistence (Neon) — requires DATABASE_URL."""
from __future__ import annotations

import argparse
import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import psycopg
from psycopg.rows import tuple_row

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("Set DATABASE_URL in .env or environment (Neon connection string).")
    return url


def _adapt_sql(sql: str) -> str:
    return sql.replace("?", "%s")


class PgResult:
    def __init__(self, cursor: psycopg.Cursor) -> None:
        self._cursor = cursor

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._cursor.fetchone()

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._cursor.fetchall()


class PgConnection:
    """Thin wrapper so existing SQL with ? placeholders keeps working."""

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def execute(self, sql: str, params: list[Any] | tuple[Any, ...] | None = None) -> PgResult:
        cur = self._conn.cursor(row_factory=tuple_row)
        cur.execute(_adapt_sql(sql), params or ())
        return PgResult(cur)

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


@contextmanager
def connect() -> Iterator[PgConnection]:
    conn = psycopg.connect(database_url(), row_factory=tuple_row)
    try:
        yield PgConnection(conn)
    finally:
        conn.close()


def _schema_statements() -> list[str]:
    """Split schema.sql into executable statements (header comments must not drop CREATEs)."""
    lines = [
        ln
        for ln in SCHEMA_PATH.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("--")
    ]
    sql = "\n".join(lines)
    return [s.strip() for s in re.split(r";\s*\n", sql) if s.strip()]


def init_db() -> None:
    statements = _schema_statements()
    with psycopg.connect(database_url()) as conn:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()


def next_run_id(con: PgConnection) -> int:
    row = con.execute(
        "SELECT COALESCE(MAX(run_id), 0) + 1 FROM scrape_runs"
    ).fetchone()
    return int(row[0])


def print_stats() -> None:
    with connect() as con:
        ingest = con.execute("SELECT COUNT(*) FROM ingest_runs").fetchone()[0]
        runs = con.execute("SELECT COUNT(*) FROM scrape_runs").fetchone()[0]
        offers = con.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
        legs = con.execute("SELECT COUNT(*) FROM leg_observations").fetchone()[0]
        pending = con.execute(
            "SELECT COUNT(*) FROM alerts WHERE status = 'new'"
        ).fetchone()[0]
        print(f"ingest_runs: {ingest}")
        print(f"scrape_runs: {runs}")
        print(f"offers: {offers}")
        print(f"leg_observations: {legs}")
        print(f"alerts (new): {pending}")
        if ingest:
            print("\nLatest ingest runs:")
            rows = con.execute(
                """
                SELECT id, provider, status, started_at, records_count
                FROM ingest_runs
                ORDER BY id DESC
                LIMIT 5
                """
            ).fetchall()
            for row in rows:
                print(
                    f"  ingest {row[0]} | {row[1]} | {row[2]} | {row[3]} | records={row[4]}"
                )


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(prog="flights.db")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="Create Postgres tables")
    sub.add_parser("stats", help="Print row counts")
    args = parser.parse_args()
    if args.cmd == "init":
        init_db()
        print("Postgres schema initialized.")
    elif args.cmd == "stats":
        print_stats()


if __name__ == "__main__":
    main()
