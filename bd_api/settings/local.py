# -*- coding: utf-8 -*-

from pathlib import Path

from bd_api.custom.logger import setup_logger
from bd_api.settings.base import *  # noqa
from bd_api.utils import getenv

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-h@^ve4439x+m8mzd7ii(l%offc65@g-t0dtb7m$(z1j2u_wzav"

# CSRF
# https://docs.djangoproject.com/en/4.2/ref/csrf/
# https://docs.djangoproject.com/en/4.2/ref/settings/#std-setting-CSRF_TRUSTED_ORIGINS
CSRF_TRUSTED_ORIGINS = ["http://localhost:8080"]

# Admins
ADMINS = []

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

# Email
# https://docs.djangoproject.com/en/4.0/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_HOST_USER = getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = getenv("EMAIL_HOST_PASSWORD")
EMAIL_PORT = int(getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = bool(getenv("EMAIL_PORT", "True"))
SERVER_EMAIL = getenv("EMAIL_HOST_USER")
DEFAULT_FROM_EMAIL = getenv("EMAIL_HOST_USER")

# Logging
setup_logger(level="DEBUG", ignore=["faker"], serialize=False)

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
...

# Stripe
STRIPE_LIVE_MODE = bool(getenv("STRIPE_LIVE_MODE", False))
STRIPE_LIVE_SECRET_KEY = getenv("STRIPE_LIVE_SECRET_KEY")
STRIPE_TEST_SECRET_KEY = getenv("STRIPE_TEST_SECRET_KEY")
DJSTRIPE_WEBHOOK_SECRET = getenv("DJSTRIPE_WEBHOOK_SECRET")
DJSTRIPE_USE_NATIVE_JSONFIELD = True
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"
