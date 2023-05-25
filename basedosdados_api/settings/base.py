# -*- coding: utf-8 -*-
"""
Django settings for basedosdados_api project.

Generated by 'django-admin startproject' using Django 4.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

from datetime import timedelta
from pathlib import Path
from os import getenv
import os


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_ROOT = BASE_DIR / "static"


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-h@^ve4439x+m8mzd7ii(l%offc65@g-t0dtb7m$(z1j2u_wzav"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]
CORS_ORIGIN_ALLOW_ALL = True


# Application definition

INSTALLED_APPS = [
    "modeltranslation",
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "graphene_django",
    "haystack",
    "health_check",
    "health_check.db",
    "health_check.cache",
    "health_check.storage",
    "health_check.contrib.migrations",
    "rest_framework",
    "basedosdados_api.account",
    "basedosdados_api.core",
    "basedosdados_api.api.v1",
    "basedosdados_api.schemas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "basedosdados_api.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "basedosdados_api.wsgi.application"


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "pt-br"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = "static/"

# Media files
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework
# https://www.django-rest-framework.org/
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "PAGE_SIZE": 20,
}

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        # Include the default Django email handler for errors
        # This is what you'd get without configuring logging at all.
        "mail_admins": {
            "class": "django.utils.log.AdminEmailHandler",
            "level": "ERROR",
            # But the emails are plain text by default - HTML is nicer
            "include_html": True,
        },
        # Log to a text file that can be rotated by logrotate
        "logfile": {
            "class": "logging.handlers.WatchedFileHandler",
            "filename": str(BASE_DIR / "django.log"),
        },
    },
    "loggers": {
        # Again, default Django configuration to email unhandled exceptions
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
        # Might as well log any errors anywhere else in Django
        "django": {
            "handlers": ["logfile"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

# Swagget configurations
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
    }
}

# Graphene configurations
GRAPHENE = {
    "SCHEMA": "basedosdados_api.api.v1.schema.schema",
    "MIDDLEWARE": [
        "graphql_jwt.middleware.JSONWebTokenMiddleware",
    ],
    "RELAY_CONNECTION_MAX_LIMIT": 1500,
}

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "graphql_jwt.backends.JSONWebTokenBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_USER_MODEL = "account.Account"

# GraphQL JWT configurations
GRAPHQL_JWT = {
    "JWT_AUTH_HEADER_PREFIX": "Bearer",
    "JWT_EXPIRATION_DELTA": timedelta(minutes=30),
    "JWT_REFRESH_EXPIRATION_DELTA": timedelta(days=1),
    "JWT_VERIFY_EXPIRATION": True,
    "JWT_ALLOW_ANY_HANDLER": "basedosdados_api.custom.allow_any.allow_any",
}

# Translations
LANGUAGES = (
    ("pt", lambda x: "Português"),
    ("en", lambda x: "English"),
    ("es", lambda x: "Español"),
)

MODELTRANSLATION_AUTO_POPULATE = True

# Cache our autogenerated schemas
GRAPHENE_SCHEMAS_CACHE = {}

ALLOWED_UPLOAD_IMAGES = ["png"]

# Haystack
HAYSTACK_CONNECTIONS = {
    "default": {
        "ENGINE": "basedosdados_api.api.v1.haystack_engines.AsciifoldingElasticSearchEngine",
        "URL": getenv("ELASTICSEARCH_URL", "http://0.0.0.0:9200"),
        "TIMEOUT": 5,
        "INDEX_NAME": getenv("ELASTICSEARCH_INDEX_NAME", "default"),
        "BATCH_SIZE": 1000,
        "INCLUDE_SPELLING": True,
    },
}
HAYSTACK_DEFAULT_OPERATOR = "OR"
HAYSTACK_FUZZY_MIN_SIM = 0.25
HAYSTACK_ITERATOR_LOAD_PER_QUERY = 200
HAYSTACK_LIMIT_TO_REGISTERED_MODELS = True
HAYSTACK_SEARCH_RESULTS_PER_PAGE = 100
HAYSTACK_SIGNAL_PROCESSOR = "haystack.signals.RealtimeSignalProcessor"

X_FRAME_OPTIONS = "SAMEORIGIN"

JAZZMIN_SETTINGS = {
    "site_title": "Base dos Dados",
    # Title on the login screen (19 chars max) (defaults to
    # current_admin_site.site_header if absent or None)
    "site_header": "Base dos Dados Admin",
    # Title on the brand (19 chars max) (defaults to
    # current_admin_site.site_header if absent or None)
    "site_brand": "Base dos Dados Admin",
    # Logo to use for your site, must be present in static files,
    # used for brand on top left
    "site_logo": "core/img/bd.png",
    # Logo to use for your site, must be present in static files,
    # used for login form logo (defaults to site_logo)
    "login_logo": None,
    # CSS classes that are applied to the admin
    "custom_css": "core/css/main.css",
    "changeform_format": "horizontal_tabs",
    "related_modal_active": True,
    "topmenu_links": [
        {"name": "Metadados", "app": "v1"},
        {"model": "v1.dataset"},
    ],
    "show_ui_builder": True,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": True,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": True,
    "brand_colour": "navbar-success",
    "accent": "accent-success",
    "navbar": "navbar-white navbar-light",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-success",
    "sidebar_nav_small_text": True,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
    "actions_sticky_top": True,
}
