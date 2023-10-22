# -*- coding: utf-8 -*-
from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.apps.api.v1"
    app_label = "v1"
