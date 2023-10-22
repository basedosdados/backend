# -*- coding: utf-8 -*-
from django.apps import AppConfig


class AccountConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bd_api.apps.account"

    def ready(self):
        import bd_api.apps.account.signals  # noqa