# -*- coding: utf-8 -*-
import os

from basedosdados_api.settings.base import *  # noqa

from django.utils.log import DEFAULT_LOGGING


def nonull_getenv(var):
    value = getenv(var)
    if value is None:
        raise ValueError(f"Environment variable {var} not set")
    return value


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "api.sqlite3",  # noqa
    }
}

LOGGING = DEFAULT_LOGGING
CSRF_TRUSTED_ORIGINS = ["http://localhost:8080"]

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "NOT SET")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "NOT SET")
EMAIL_PORT = 587
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.getenv("EMAIL_HOST_USER", "NOT SET")
SERVER_EMAIL = os.getenv("EMAIL_HOST_USER", "NOT SET")
