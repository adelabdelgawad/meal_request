"""
Datetime utilities for consistent UTC handling across the application.

CRITICAL: Always use these utilities for datetime operations to ensure:
1. All datetimes are timezone-aware (UTC)
2. Database storage is consistent
3. API responses include proper timezone information
"""

from datetime import datetime, timezone
from typing import Optional


def utcnow() -> datetime:
    """
    Get current UTC time as a timezone-aware datetime.

    Use this instead of datetime.now() or datetime.utcnow().

    Returns:
        datetime: Current time in UTC with timezone information

    Example:
        >>> from utils.datetime_utils import utcnow
        >>> now = utcnow()
        >>> print(now)  # 2025-12-12 15:00:00+00:00
    """
    return datetime.now(timezone.utc)


def make_aware(dt: datetime, tz: timezone = timezone.utc) -> datetime:
    """
    Convert a naive datetime to a timezone-aware datetime.

    Args:
        dt: Naive datetime to convert
        tz: Timezone to use (defaults to UTC)

    Returns:
        datetime: Timezone-aware datetime

    Raises:
        ValueError: If datetime is already timezone-aware

    Example:
        >>> from datetime import datetime
        >>> naive_dt = datetime(2025, 12, 12, 15, 0, 0)
        >>> aware_dt = make_aware(naive_dt)
        >>> print(aware_dt)  # 2025-12-12 15:00:00+00:00
    """
    if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
        raise ValueError("Datetime is already timezone-aware")
    return dt.replace(tzinfo=tz)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure a datetime is in UTC timezone.

    - If None, returns None
    - If naive, assumes it's UTC and makes it aware
    - If aware but not UTC, converts to UTC
    - If already UTC-aware, returns as-is

    Args:
        dt: Datetime to convert

    Returns:
        Optional[datetime]: UTC timezone-aware datetime or None

    Example:
        >>> from datetime import datetime, timezone, timedelta
        >>> # Naive datetime - assumes UTC
        >>> naive = datetime(2025, 12, 12, 15, 0, 0)
        >>> utc = ensure_utc(naive)
        >>> print(utc)  # 2025-12-12 15:00:00+00:00

        >>> # Aware datetime in different timezone - converts to UTC
        >>> cairo_tz = timezone(timedelta(hours=2))
        >>> cairo_dt = datetime(2025, 12, 12, 17, 0, 0, tzinfo=cairo_tz)
        >>> utc = ensure_utc(cairo_dt)
        >>> print(utc)  # 2025-12-12 15:00:00+00:00
    """
    if dt is None:
        return None

    # If naive, assume it's UTC and make it aware
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=timezone.utc)

    # If already aware, convert to UTC
    return dt.astimezone(timezone.utc)


def to_utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """
    Convert datetime to ISO 8601 string with UTC timezone.

    Args:
        dt: Datetime to convert

    Returns:
        Optional[str]: ISO 8601 string with 'Z' suffix or None

    Example:
        >>> from datetime import datetime
        >>> dt = datetime(2025, 12, 12, 15, 0, 0, tzinfo=timezone.utc)
        >>> iso = to_utc_iso(dt)
        >>> print(iso)  # "2025-12-12T15:00:00Z"
    """
    if dt is None:
        return None

    utc_dt = ensure_utc(dt)
    # Use isoformat() and replace '+00:00' with 'Z' for cleaner output
    return utc_dt.isoformat().replace('+00:00', 'Z')


# Backward compatibility - export common datetime classes
__all__ = [
    'utcnow',
    'make_aware',
    'ensure_utc',
    'to_utc_iso',
    'datetime',
    'timezone',
]
