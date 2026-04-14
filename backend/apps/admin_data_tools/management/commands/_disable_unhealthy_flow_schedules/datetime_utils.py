# -*- coding: utf-8 -*-
from datetime import datetime, timedelta


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def one_week_ago() -> str:
    from django.utils import timezone

    return (timezone.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
