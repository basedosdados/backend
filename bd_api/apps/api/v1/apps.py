# -*- coding: utf-8 -*-
from django.apps import AppConfig


class ApiConfig(AppConfig):
    app_label = "v1"
    verbose_name = " V1"
    name = "bd_api.apps.api.v1"
    default_auto_field = "django.db.models.BigAutoField"
