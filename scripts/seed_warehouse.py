"""Create sample DuckDB warehouse for the bootcamp."""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "warehouse.duckdb"


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    con = duckdb.connect(str(DB_PATH))
    con.execute("""
        CREATE TABLE regions (
            region_id INTEGER PRIMARY KEY,
            region_name VARCHAR
        );
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            region_id INTEGER,
            order_date DATE,
            amount_usd DOUBLE,
            status VARCHAR
        );
    """)
    con.execute("""
        INSERT INTO regions VALUES
            (1, 'North'), (2, 'South'), (3, 'EMEA'), (4, 'APAC');
    """)
    con.executemany(
        """
        INSERT INTO orders VALUES (?, ?, ?, ?, ?)
        """,
        [
            (1, 1, "2026-04-01", 120.5, "completed"),
            (2, 1, "2026-04-02", 80.0, "completed"),
            (3, 2, "2026-04-03", 200.0, "completed"),
            (4, 3, "2026-04-04", 50.0, "refunded"),
            (5, 4, "2026-04-05", 300.0, "completed"),
            (6, 1, "2026-03-15", 90.0, "completed"),
            (7, 3, "2026-03-20", 150.0, "completed"),
        ],
    )
    con.close()
    print(f"Seeded {DB_PATH}")


if __name__ == "__main__":
    main()
