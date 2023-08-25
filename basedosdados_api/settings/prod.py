# -*- coding: utf-8 -*-
from json import loads

from google.oauth2 import service_account

from basedosdados_api.settings.base import *  # noqa
from utils import getenv


def get_admins():
    admins = getenv("ADMINS")
    if admins is None:
        return []
    return [admin.split(",") for admin in admins.split(";")]


DEBUG = False
SECRET_KEY = getenv("DJANGO_SECRET_KEY")

# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": getenv("DB_NAME"),
        "USER": getenv("DB_USER"),
        "PASSWORD": getenv("DB_PASSWORD"),
        "HOST": getenv("DB_HOST"),
        "PORT": getenv("DB_PORT"),
    }
}

ADMINS = get_admins()

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_HOST_USER = getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = getenv("EMAIL_HOST_PASSWORD")
EMAIL_PORT = int(getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = bool(getenv("EMAIL_PORT", "True"))
SERVER_EMAIL = getenv("EMAIL_HOST_USER")
DEFAULT_FROM_EMAIL = getenv("EMAIL_HOST_USER")

# Set logging path for production
# LOGGING["handlers"]["logfile"][  # noqa
#     "filename"
# ] = "/var/log/django/basedosdados_api.log"

# Google Cloud Storage
GS_SERVICE_ACCOUNT = getenv("GCP_SA")
GS_CREDENTIALS = service_account.Credentials.from_service_account_info(loads(GS_SERVICE_ACCOUNT))
GS_BUCKET_NAME = getenv("GCP_BUCKET_NAME")
GS_EXPIRATION = timedelta(seconds=604800)  # noqa: F405
DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"

GOOGLE_APPLICATION_CREDENTIALS = getenv("GOOGLE_APPLICATION_CREDENTIALS")
