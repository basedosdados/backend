# -*- coding: utf-8 -*-
from django.apps import AppConfig


class AccountConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.apps.account"

    def ready(self):
        import apps.apps.account.signals  # noqa
