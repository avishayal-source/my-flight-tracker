from datetime import date, datetime, time, timedelta

from flights.config import AppConfig
from flights.db import connect, init_db
from flights.ingest import run_once
from flights.analyze import cheapest_roundtrips


def test_cheapest_roundtrip(tmp_path, monkeypatch):
    db = tmp_path / "t.duckdb"
    cfg = AppConfig(
        origin="TLV",
        destination="VIE",
        horizon_days=10,
        departure_start_offset_days=0,
        direct_only=True,
        adults=2,
        cabin="ECONOMY",
        currency="USD",
        interval_seconds=3600,
        database_path=db,
    )
    monkeypatch.setattr("flights.config.load_config", lambda: cfg)
    monkeypatch.setattr("flights.db.load_config", lambda: cfg)
    monkeypatch.setattr("flights.ingest.load_config", lambda: cfg)
    monkeypatch.setattr("flights.analyze.load_config", lambda: cfg)

    init_db(db)
    run_once("mock", max_days=10, headful=False, start_offset_days=None)

    opts = cheapest_roundtrips([4], run_id=1)
    assert len(opts) == 1
    o = opts[0]
    assert o.trip_days == 4
    assert date.fromisoformat(o.return_date) == date.fromisoformat(o.outbound_date) + timedelta(days=4)
