"""CLI wrapper for run comparison."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flights.compare_runs import (
    compare_runs_summary,
    departure_date_price_over_runs,
    price_vs_days_to_departure,
    same_flight_price_over_runs,
)

if __name__ == "__main__":
    print(compare_runs_summary())
    print()
    print(departure_date_price_over_runs("TLV_VIE", "2026-05-22"))
    print()
    print(price_vs_days_to_departure("TLV_VIE"))
