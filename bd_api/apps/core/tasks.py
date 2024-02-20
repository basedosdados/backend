# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from huey import crontab
from huey.contrib.djhuey import periodic_task

from bd_api.apps.core.models import Metadata
from bd_api.custom.client import BetterStackClient
from bd_api.custom.environment import production_task


@periodic_task(crontab(day="1", hour="3", minute="0"))
@production_task
def get_monitor_availability():
    """Get availability metric and save as metadata"""

    def get_period():
        """Get last month period as tuple of strings"""

        today = datetime.today()
        since = datetime(today.year, today.month - 1, 1)
        until = datetime(today.year, today.month, 1) - timedelta(days=1)
        return since.strftime("%Y-%m-%d"), until.strftime("%Y-%m-%d")

    since, until = get_period()
    client = BetterStackClient()
    for monitor in client.get_monitors():
        Metadata.objects.create(
            key={
                "since": since,
                "until": until,
                "monitor_id": monitor["id"],
                "monitor_url": monitor["attributes"]["url"],
            },
            value=client.get_monitor_summary(monitor["id"], since, until),
        )
