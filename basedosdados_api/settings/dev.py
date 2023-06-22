# -*- coding: utf-8 -*-
"""
Django dev settings for basedosdados_api project.
"""

import os

from django.utils.log import DEFAULT_LOGGING
from basedosdados_api.settings.base import *  # pylint: disable=wildcard-import,unused-wildcard-import # noqa: F403,F401


def nonull_getenv(var):
    """Get environment variable or raise exception if not set."""
    value = getenv(var)  # noqa: F405
    if value is None:
        raise ValueError(f"Environment variable {var} not set")
    return value


CSRF_TRUSTED_ORIGINS = ["http://localhost:3000", "http://localhost:8000"]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/
BASE_DIR = Path(__file__).resolve().parent.parent  # noqa: F405
STATIC_ROOT = BASE_DIR / "staticfiles"


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

INSTALLED_APPS += ["django_extensions"]  # noqa: F405
