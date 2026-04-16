# -*- coding: utf-8 -*-
from django.core.management import call_command
from huey import crontab
from huey.contrib.djhuey import db_periodic_task

from backend.custom.environment import production_task


@db_periodic_task(crontab(minute="*/20"))
@production_task
def disable_unhealthy_flow_schedules():
    """Disable unhealthy flow schedules"""
    call_command("disable_unhealthy_flow_schedules")
