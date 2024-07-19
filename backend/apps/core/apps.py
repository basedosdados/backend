# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.apps.core"
    app_label = "core"

    def ready(self):
        import backend.apps.core.signals  # noqa
