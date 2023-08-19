# -*- coding: utf-8 -*-
from json import loads
from os import getenv

from google.oauth2 import service_account

from basedosdados_api.settings.base import *  # noqa


def nonull_getenv(var, default=None):
    """Get environment variable or raise exception if not set."""
    value = getenv(var, default)
    if value is None:
        raise ValueError(f"Environment variable {var} not set")
    return value


def get_admins():
    admins = getenv("ADMINS")
    if admins is None:
        return []
    return [admin.split(",") for admin in admins.split(";")]


DEBUG = False
SECRET_KEY = nonull_getenv("DJANGO_SECRET_KEY")

# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": nonull_getenv("DB_NAME"),
        "USER": nonull_getenv("DB_USER"),
        "PASSWORD": nonull_getenv("DB_PASSWORD"),
        "HOST": nonull_getenv("DB_HOST"),
        "PORT": nonull_getenv("DB_PORT"),
    }
}

ADMINS = get_admins()

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_HOST_USER = nonull_getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = nonull_getenv("EMAIL_HOST_PASSWORD")
EMAIL_PORT = int(nonull_getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = bool(nonull_getenv("EMAIL_PORT", "True"))
SERVER_EMAIL = nonull_getenv("EMAIL_HOST_USER")
DEFAULT_FROM_EMAIL = nonull_getenv("EMAIL_HOST_USER")

# Set logging path for production
# LOGGING["handlers"]["logfile"][  # noqa
#     "filename"
# ] = "/var/log/django/basedosdados_api.log"

# Google Cloud Storage
GS_SERVICE_ACCOUNT = nonull_getenv("GCP_SA")
GS_CREDENTIALS = service_account.Credentials.from_service_account_info(
    loads(GS_SERVICE_ACCOUNT)
)
GS_BUCKET_NAME = nonull_getenv("GCP_BUCKET_NAME")
GS_EXPIRATION = timedelta(seconds=604800)  # noqa: F405
DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"

GOOGLE_APPLICATION_CREDENTIALS = nonull_getenv("GOOGLE_APPLICATION_CREDENTIALS")
