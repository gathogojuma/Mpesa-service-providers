"""
Timezone helpers for TillTrack.

All "today" / "day boundary" calculations should use these helpers so that
a business in Nairobi sees their day roll over at midnight EAT (UTC+3),
not at midnight UTC.

Usage:
    from ..utils.timezone import now_local, today_start_local, today_end_local

    start = today_start_local()  # e.g. 2026-09-11 00:00:00+03:00
    end   = today_end_local()    # e.g. 2026-09-12 00:00:00+03:00
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..config import settings


def get_tz() -> ZoneInfo:
    """Return the configured timezone as a ZoneInfo object."""
    return ZoneInfo(settings.TIMEZONE)


def now_local() -> datetime:
    """
    Return the current time in the configured timezone.

    Note: returns a timezone-aware datetime.
    """
    return datetime.now(get_tz())


def today_start_local() -> datetime:
    """
    Return the start of today (00:00:00) in the configured timezone.

    Returned datetime is timezone-aware and can be compared directly
    against timezone-aware DB timestamps.
    """
    n = now_local()
    return n.replace(hour=0, minute=0, second=0, microsecond=0)


def today_end_local() -> datetime:
    """Return the start of tomorrow (00:00:00) in the configured timezone."""
    return today_start_local() + timedelta(days=1)


def to_local(dt: datetime) -> datetime:
    """
    Convert a datetime to the configured timezone.

    If the datetime is naive (no tzinfo), it's assumed to already be in
    the configured timezone. If it's aware, it's converted to the configured
    timezone. Safe to call on values straight out of the database.
    """
    tz = get_tz()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)
