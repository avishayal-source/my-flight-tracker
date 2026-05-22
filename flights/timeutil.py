"""Time helpers for ingest idempotency buckets."""
from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def observed_at_bucket(dt: datetime | None = None, window_minutes: int = 30) -> datetime:
    """Floor UTC time to a fixed window (default 30 minutes)."""
    dt = dt or utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    minute = (dt.minute // window_minutes) * window_minutes
    return dt.replace(minute=minute, second=0, microsecond=0)
