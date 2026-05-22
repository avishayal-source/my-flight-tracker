import os
from datetime import date, timedelta

import pytest

from flights.analyze import cheapest_roundtrips
from flights.ingest import run_once

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_DB_TESTS"),
    reason="Set RUN_DB_TESTS=1 and DATABASE_URL for Postgres integration tests",
)


def test_cheapest_roundtrip():
    run_once("mock", max_days=10, headful=False, start_offset_days=None)
    opts = cheapest_roundtrips([4], run_id=1)
    assert len(opts) == 1
    o = opts[0]
    assert o.trip_days == 4
    assert date.fromisoformat(o.return_date) == date.fromisoformat(
        o.outbound_date
    ) + timedelta(days=4)
