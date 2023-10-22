# -*- coding: utf-8 -*-
from django.apps import AppConfig


class AccountConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.apps.account"

    def ready(self):
        import app.apps.account.signals  # noqa
