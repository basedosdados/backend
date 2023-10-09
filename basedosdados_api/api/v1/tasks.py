# -*- coding: utf-8 -*-
from huey import crontab
from huey.contrib.djhuey import periodic_task
from loguru import logger

from basedosdados_api.api.v1.admin import update_table_metadata


@periodic_task(crontab(minute="*/10"))
def every_ten_mins_task():
    logger.info("Am I alive between these periods?")


@periodic_task(crontab(day_of_week="0", hour="0", minute="0"))
def update_table_metadata_task():
    update_table_metadata()
