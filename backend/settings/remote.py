# -*- coding: utf-8 -*-

from datetime import timedelta
from json import loads
from os import getenv

from google.oauth2 import service_account

from backend.settings.base import *  # noqa

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = getenv("DJANGO_SECRET_KEY")

# CSRF
# https://docs.djangoproject.com/en/4.2/ref/csrf/
# https://docs.djangoproject.com/en/4.2/ref/settings/#std-setting-CSRF_TRUSTED_ORIGINS
...

# Admins
ADMINS = [admin.split(",") for admin in getenv("ADMINS", "").split(";")]

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
LOGGING_CONFIG = "backend.custom.logger.setup_logger"

# Google Auth
GOOGLE_APPLICATION_CREDENTIALS = getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Google Directory
GOOGLE_DIRECTORY_SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.user",
    "https://www.googleapis.com/auth/admin.directory.group",
]
GOOGLE_DIRECTORY_SUBJECT = getenv("GOOGLE_DIRECTORY_SUBJECT")
GOOGLE_DIRECTORY_GROUP_KEY = getenv("GOOGLE_DIRECTORY_GROUP_KEY")

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
def as_bool(var):
    if isinstance(var, str):
        if var.lower() in ["true", "t", "1"]:
            return True
    return False


STRIPE_LIVE_MODE = as_bool(getenv("STRIPE_LIVE_MODE"))
STRIPE_LIVE_SECRET_KEY = getenv("STRIPE_LIVE_SECRET_KEY")
STRIPE_TEST_SECRET_KEY = getenv("STRIPE_TEST_SECRET_KEY")
DJSTRIPE_WEBHOOK_SECRET = getenv("DJSTRIPE_WEBHOOK_SECRET")
DJSTRIPE_USE_NATIVE_JSONFIELD = True
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID = getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = getenv("GOOGLE_OAUTH_CLIENT_SECRET")