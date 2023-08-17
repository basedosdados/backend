# -*- coding: utf-8 -*-
from django.apps import AppConfig


class AccountConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "basedosdados_api.account"

    def ready(self):
        import basedosdados_api.account.signals
