"""Flag suspicious rows in the flight warehouse."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import duckdb

con = duckdb.connect("data/flights.duckdb")
runs = con.execute("SELECT COUNT(*) FROM scrape_runs").fetchone()[0]
offers = con.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
print(f"runs={runs} offers={offers}")

dup296 = con.execute(
    "SELECT COUNT(*) FROM offers WHERE price_total_usd = 296"
).fetchone()[0]
unk = con.execute(
    "SELECT COUNT(*) FROM offers WHERE carrier_code = 'UNK'"
).fetchone()[0]
print(f"rows with price exactly 296: {dup296} ({100*dup296/max(offers,1):.0f}%)")
print(f"rows with carrier UNK: {unk}")

if dup296 > offers * 0.3:
    print("WARNING: many $296 rows — likely bad scrape (UI chip, not a fare).")
if unk > offers * 0.3:
    print("WARNING: many UNK carriers — parser did not read airline names.")

print("\nSample latest run:")
for r in con.execute(
    """
    SELECT departure_date, direction, price_total_usd, carrier_code, flight_number
    FROM offers WHERE run_id = (SELECT MAX(run_id) FROM scrape_runs)
    ORDER BY direction, departure_date LIMIT 10
    """
).fetchall():
    print(f"  {r}")
con.close()
