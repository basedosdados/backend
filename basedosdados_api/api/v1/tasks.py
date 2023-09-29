# -*- coding: utf-8 -*-
from huey import crontab
from huey.contrib.djhuey import periodic_task


@periodic_task(crontab(minute="*/10"))
def every_ten_mins():
    print("It's been ten minutes!")
