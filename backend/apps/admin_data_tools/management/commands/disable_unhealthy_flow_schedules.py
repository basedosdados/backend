# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from ._disable_unhealthy_flow_schedules.service import FlowService


class Command(BaseCommand):
    """Management command to detect and disable unhealthy Prefect flow schedules.

    Runs the two-phase pipeline defined in ``FlowService``:

    1. Re-enforces flows that should remain disabled but were reactivated by
       Prefect (e.g. after re-registration), and detects new failures in flows
       that were previously reactivated by an admin.
    2. Detects new untracked flows that have been failing, disables them in
       Prefect, registers them in the database, and sends a Discord notification.
    """

    help = "Disable unhealthy flow schedules"

    def handle(self, *args, **options) -> None:
        """Execute the command.

        Args:
            *args: Unused positional arguments.
            **options: Unused keyword arguments.
        """
        FlowService().disable_unhealthy_flow_schedules()
