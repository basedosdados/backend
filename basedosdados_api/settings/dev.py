# -*- coding: utf-8 -*-
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

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_HOST_USER = nonull_getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = nonull_getenv("EMAIL_HOST_PASSWORD")
EMAIL_PORT = 587
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = nonull_getenv("EMAIL_HOST_USER")
SERVER_EMAIL = nonull_getenv("EMAIL_HOST_USER")
