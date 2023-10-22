# -*- coding: utf-8 -*-

from datetime import timedelta
from json import loads

from google.oauth2 import service_account

from apps.logger import setup_logger
from apps.settings.base import *  # noqa
from apps.utils import getadmins, getenv

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = getenv("DJANGO_SECRET_KEY")

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
        "NAME": getenv("DB_NAME"),
        "USER": getenv("DB_USER"),
        "PASSWORD": getenv("DB_PASSWORD"),
        "HOST": getenv("DB_HOST"),
        "PORT": getenv("DB_PORT"),
    }
}

# Email
# https://docs.djangoproject.com/en/4.0/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_HOST_USER = getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = getenv("EMAIL_HOST_PASSWORD")
EMAIL_PORT = int(getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = bool(getenv("EMAIL_PORT", "True"))
SERVER_EMAIL = getenv("EMAIL_HOST_USER")
DEFAULT_FROM_EMAIL = getenv("EMAIL_HOST_USER")

# Logging
setup_logger(level="INFO", serialize=True)

# Google Application Credentials
GOOGLE_APPLICATION_CREDENTIALS = getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

# Google Cloud Storage
GS_SERVICE_ACCOUNT = getenv("GCP_SA")
GS_CREDENTIALS = service_account.Credentials.from_service_account_info(loads(GS_SERVICE_ACCOUNT))
GS_BUCKET_NAME = getenv("GCP_BUCKET_NAME")
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
STRIPE_LIVE_SECRET_KEY = getenv("STRIPE_LIVE_SECRET_KEY", "")
STRIPE_TEST_SECRET_KEY = getenv("STRIPE_TEST_SECRET_KEY", "")
STRIPE_LIVE_MODE = True
DJSTRIPE_WEBHOOK_SECRET = getenv("STRIPE_WEBHOOK_SECRET", "")
DJSTRIPE_USE_NATIVE_JSONFIELD = True
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"
