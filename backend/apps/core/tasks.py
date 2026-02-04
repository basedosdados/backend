# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from django.core.management import call_command
from huey import crontab
from huey.contrib.djhuey import db_periodic_task

from backend.apps.core.models import Metadata
from backend.custom.client import BetterStackClient
from backend.custom.environment import not_production_task, production_task
from backend.custom.task_decorators import log_task_execution


@db_periodic_task(crontab(day="1", hour="3", minute="0"))
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


@db_periodic_task(crontab(day_of_week="monday", hour="3", minute="0"))
@not_production_task
@log_task_execution("sync_database_with_prod")
def sync_database_with_prod():
    """Sync database with production"""
    call_command("fetch_metabase")
    call_command("populate")
    return "Sincronização concluída com sucesso"


@db_periodic_task(crontab(minute="*/20"))
# @production_task
def disable_unhealthy_flow_schedules():
    """Disable unhealthy flow schedules"""
    call_command("disable_unhealthy_flow_schedules")
