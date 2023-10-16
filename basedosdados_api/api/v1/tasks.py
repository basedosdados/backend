# -*- coding: utf-8 -*-
from huey import crontab
from huey.contrib.djhuey import periodic_task
from loguru import logger

from basedosdados_api.api.v1.admin import update_table_metadata
from basedosdados_api.logger import setup_logger
from basedosdados_api.utils import is_remote, prod_task

level = "INFO" if is_remote() else "DEBUG"
serialize = True if is_remote() else False
setup_logger(level=level, serialize=serialize)


@periodic_task(crontab(minute="*/10"))
def every_ten_mins_task():
    logger.info("Am I alive between these periods?")


@prod_task
@periodic_task(crontab(day_of_week="0", hour="0", minute="0"))
def update_table_metadata_task():
    update_table_metadata()
