# -*- coding: utf-8 -*-

from datetime import timedelta
from json import loads

from google.oauth2 import service_account

from bd_api.custom.logger import setup_logger
from bd_api.settings.base import *  # noqa
from bd_api.utils import getadmins, getenvp

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = getenvp("DJANGO_SECRET_KEY")

# CSRF
# https://docs.djangoproject.com/en/4.2/ref/csrf/
# https://docs.djangoproject.com/en/4.2/ref/settings/#std-setting-CSRF_TRUSTED_ORIGINS
...

# Admins
ADMINS = getadmins()

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/
STATIC_URL = "static/"

# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": getenvp("DB_NAME"),
        "USER": getenvp("DB_USER"),
        "PASSWORD": getenvp("DB_PASSWORD"),
        "HOST": getenvp("DB_HOST"),
        "PORT": getenvp("DB_PORT"),
    }
}

# Email
# https://docs.djangoproject.com/en/4.0/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_HOST_USER = getenvp("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = getenvp("EMAIL_HOST_PASSWORD")
EMAIL_PORT = int(getenvp("EMAIL_PORT", "587"))
EMAIL_USE_TLS = bool(getenvp("EMAIL_PORT", "True"))
SERVER_EMAIL = getenvp("EMAIL_HOST_USER")
DEFAULT_FROM_EMAIL = getenvp("EMAIL_HOST_USER")

# Logging
setup_logger(level="INFO", ignore=["faker"], serialize=True)

# Google Application Credentials
GOOGLE_APPLICATION_CREDENTIALS = getenvp("GOOGLE_APPLICATION_CREDENTIALS", "")

# Google Cloud Storage
GS_SERVICE_ACCOUNT = getenvp("GCP_SA")
GS_CREDENTIALS = service_account.Credentials.from_service_account_info(loads(GS_SERVICE_ACCOUNT))
GS_BUCKET_NAME = getenvp("GCP_BUCKET_NAME")
GS_EXPIRATION = timedelta(seconds=604800)
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Stripe
STRIPE_LIVE_MODE = bool(getenvp("STRIPE_LIVE_MODE"))
STRIPE_LIVE_SECRET_KEY = getenvp("STRIPE_LIVE_SECRET_KEY")
STRIPE_TEST_SECRET_KEY = getenvp("STRIPE_TEST_SECRET_KEY")
DJSTRIPE_WEBHOOK_SECRET = getenvp("DJSTRIPE_WEBHOOK_SECRET")
DJSTRIPE_USE_NATIVE_JSONFIELD = True
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"
