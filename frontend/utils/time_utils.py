"""
IST timestamp formatting utilities for NIYAM-AI frontend.

Converts UTC audit timestamps to Indian Standard Time (Asia/Kolkata) for
display purposes. Backend storage and audit logs remain in UTC.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


# IST (Indian Standard Time) timezone
try:
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    # Fallback for environments without tzdata (e.g., Windows Python 3.13)
    # IST is UTC+5:30 year-round (no DST)
    IST = timezone(timedelta(hours=5, minutes=30))


def parse_utc_timestamp(value: str | datetime | None) -> datetime | None:
    """
    Parse a UTC timestamp string or datetime into a timezone-aware UTC datetime.

    Handles:
    - ISO 8601 strings with Z suffix (e.g., "2026-05-22T13:11:45Z")
    - ISO 8601 strings with +00:00 offset
    - timezone-aware datetimes
    - naive datetimes (assumed UTC)
    - None or empty values (returns None)
    - Invalid formats (returns None)

    Args:
        value: ISO timestamp string, datetime, or None

    Returns:
        timezone-aware datetime in UTC, or None if parsing fails
    """

    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            # Normalize Z to +00:00 offset
            normalized = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
        except (ValueError, TypeError, AttributeError):
            return None

    try:
        # Normalize Z to +00:00 offset
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except (ValueError, TypeError):
        return None

    # Ensure timezone is set
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    # Convert to UTC if necessary
    return parsed.astimezone(timezone.utc)


def convert_utc_to_ist(value: str | datetime | None) -> datetime | None:
    """
    Convert a UTC timestamp or datetime to an IST datetime.

    Args:
        value: ISO timestamp string, datetime, or None

    Returns:
        IST-aware datetime, or None if parsing fails
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = parse_utc_timestamp(value)

    if parsed is None:
        return None

    return parsed.astimezone(IST)


def format_timestamp_short(value: str | datetime | None) -> str:
    """
    Format a UTC timestamp as short IST display: HH:MM PM/AM IST.

    Used in event cards and live monitors for compact time display.

    Args:
        value: ISO timestamp string or None

    Returns:
        Formatted string like "07:11 PM IST" or "-" if invalid
    """

    parsed = parse_utc_timestamp(value)
    if parsed is None:
        return "-"

    # Convert UTC to IST
    ist_time = parsed.astimezone(IST)

    # Format: HH:MM PM/AM IST
    return ist_time.strftime("%I:%M %p IST")


def format_timestamp_full(value: str | datetime | None) -> str:
    """
    Format a UTC timestamp as full IST display: DD Mon YYYY • HH:MM PM/AM IST.

    Used in audit logs and detailed tables for comprehensive timestamp display.

    Args:
        value: ISO timestamp string or None

    Returns:
        Formatted string like "22 May 2026 • 07:11 PM IST" or "-" if invalid
    """

    parsed = parse_utc_timestamp(value)
    if parsed is None:
        return "-"

    # Convert UTC to IST
    ist_time = parsed.astimezone(IST)

    # Format: DD Mon YYYY • HH:MM PM/AM IST
    return ist_time.strftime("%d %b %Y • %I:%M %p IST")


def format_timestamp_table(value: str | datetime | None) -> str:
    """
    Format a UTC timestamp as compact IST for table cells: YYYY-MM-DD HH:MM IST.

    Used in dense tables where space is constrained.

    Args:
        value: ISO timestamp string or None

    Returns:
        Formatted string like "2026-05-22 19:41 IST" or "-" if invalid
    """

    parsed = parse_utc_timestamp(value)
    if parsed is None:
        return "-"

    # Convert UTC to IST
    ist_time = parsed.astimezone(IST)

    # Format: YYYY-MM-DD HH:MM IST
    return ist_time.strftime("%Y-%m-%d %H:%M IST")
