# -*- coding: utf-8 -*-
from django.core.management import call_command
from huey import crontab
from huey.contrib.djhuey import db_periodic_task


@db_periodic_task(crontab(day_of_week="1-5", hour="4", minute="0"))
def check_for_updates_and_send_emails():
    call_command("send_notification")
