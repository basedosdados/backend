# -*- coding: utf-8 -*-
from huey import crontab
from huey.contrib.djhuey import periodic_task

from bd_api.apps.api.v1.admin import update_table_metadata
from bd_api.logger import setup_logger
from bd_api.utils import is_remote, prod_task

level = "INFO" if is_remote() else "DEBUG"
serialize = True if is_remote() else False
setup_logger(level=level, serialize=serialize)


@periodic_task(crontab(minute="*/10"))
def healthcheck_task():
    ...


@prod_task
@periodic_task(crontab(day_of_week="0", hour="0", minute="0"))
def update_table_metadata_task():
    update_table_metadata()
