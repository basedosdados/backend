# -*- coding: utf-8 -*-
from django.apps import AppConfig


class AuthConfig(AppConfig):
    name = "backend.apps.account_auth"
    verbose_name = "Autenticação e Autorização Interna"
    default_auto_field = "django.db.models.BigAutoField"
