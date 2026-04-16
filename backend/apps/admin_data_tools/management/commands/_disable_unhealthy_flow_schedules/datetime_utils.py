# -*- coding: utf-8 -*-
from datetime import datetime, timedelta


def parse_datetime(value: str) -> datetime:
    """Parse an ISO 8601 string into a datetime object.

    Args:
        value: ISO 8601 formatted datetime string.

    Returns:
        Parsed datetime object.
    """
    return datetime.fromisoformat(value)


def one_week_ago() -> str:
    """Return a timestamp string representing exactly one week ago.

    Returns:
        UTC timestamp formatted as ``%Y-%m-%dT%H:%M:%SZ``.
    """
    from django.utils import timezone

    return (timezone.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
