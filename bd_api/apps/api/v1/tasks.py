# -*- coding: utf-8 -*-
from django.core.management import call_command
from huey import crontab
from huey.contrib.djhuey import periodic_task

from bd_api.apps.api.v1.admin import update_table_metadata
from bd_api.custom.logger import setup_logger
from bd_api.utils import is_remote, prod_task

level = "INFO" if is_remote() else "DEBUG"
serialize = True if is_remote() else False
setup_logger(level=level, serialize=serialize)


@periodic_task(crontab(hour="*"))
def healthcheck_task():
    ...


@prod_task
@periodic_task(crontab(day_of_week="0", hour="3", minute="0"))
def update_table_metadata_task():
    update_table_metadata()


@prod_task
@periodic_task(crontab(day_of_week="1-6", hour="5", minute="0"))
def update_search_index_task():
    call_command("update_index", batchsize=100, workers=4)


@prod_task
@periodic_task(crontab(day_of_week="0", hour="5", minute="0"))
def rebuild_search_index_task():
    call_command("rebuild_index", interactive=False, batchsize=100, workers=4)
