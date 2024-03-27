# -*- coding: utf-8 -*-
from django.apps import AppConfig


class AccountConfig(AppConfig):
    name = "bd_api.apps.account"
    verbose_name = "Contas"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import bd_api.apps.account.signals  # noqa
