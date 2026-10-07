# -*- coding: utf-8 -*-
"""Shared logic for arming/disarming a flow's Prefect schedule.

Three different triggers call into this — a manual edit in the Django admin,
the admin's bulk actions/`list_editable`, and ``SetScheduleActiveView`` (API)
— and all of them need the exact same three writes. Keeping it in one place
means a future field or ordering change only needs to happen once.
"""

from datetime import datetime, timezone

from ._prefect3_client import Prefect3Client
from .models import DisabledFlowSchedule


def apply_schedule_state(record: DisabledFlowSchedule, active: bool) -> None:
    """Arm or disarm one flow's schedule — Prefect first, then the database.

    Prefect is called before the database is touched, so a Prefect failure
    leaves the stored state untouched rather than recording a change that
    never reached the scheduler. Callers that need a no-op check for an
    already-matching state do it themselves before calling this — it always
    performs the write.

    Args:
        record: the ``DisabledFlowSchedule`` row to update.
        active: desired ``is_schedule_active`` value.
    """
    Prefect3Client().set_paused(record.deployment_id, paused=not active)

    record.is_schedule_active = active
    record.reactivated_at = datetime.now(tz=timezone.utc) if active else None
    record.save(update_fields=["is_schedule_active", "reactivated_at"])
