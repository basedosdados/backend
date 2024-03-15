# -*- coding: utf-8 -*-
# ruff: noqa

import os
import sys

sys.path.append(".")
os.environ.setdefault("LOGGER_LEVEL", "INFO")
os.environ.setdefault("LOGGER_SERIALIZE", "")
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bd_api.settings")

import django

django.setup()

from bd_api.apps.api.v1.models import (
    Column as C,
    Coverage as CV,
    Dataset as D,
    DateTimeRange as DT,
    Table as T,
)


...
