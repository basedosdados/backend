# -*- coding: utf-8 -*-
"""
Django settings for bd_api project.

Generated by 'django-admin startproject' using Django 4.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

from datetime import timedelta
from os import getenv, path
from pathlib import Path

from bd_api.custom.logger import InterceptHandler

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_ROOT = BASE_DIR / "static"


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

ALLOWED_HOSTS = ["*"]
CORS_ORIGIN_ALLOW_ALL = True


# Application definition

INSTALLED_APPS = [
    "jazzmin",
    "modeltranslation",
    #
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "health_check",
    "health_check.db",
    #
    "corsheaders",
    "ordered_model",
    "haystack",
    "graphene_django",
    "django_extensions",
    "huey.contrib.djhuey",
    #
    "bd_api.apps.account",
    "bd_api.apps.core",
    "bd_api.apps.api.v1",
    "bd_api.apps.payment.apps.PaymentsConfig",
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
    "bd_api.custom.middleware.LoggerMiddleware",
]

ROOT_URLCONF = "bd_api.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [path.join(BASE_DIR, "templates")],
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

WSGI_APPLICATION = "bd_api.wsgi.application"


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

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "intercept": {
            "()": InterceptHandler,
            "level": None,
        }
    },
    "loggers": {
        "django.request": {
            "handlers": ["intercept"],
            "level": None,
            "propagate": True,
        },
        "django": {
            "handlers": ["intercept"],
            "level": None,
            "propagate": True,
        },
    },
}


# Graphene configurations
GRAPHENE = {
    "SCHEMA": "bd_api.apps.api.v1.schema.schema",
    "MIDDLEWARE": [
        "graphql_jwt.middleware.JSONWebTokenMiddleware",
    ],
    "RELAY_CONNECTION_MAX_LIMIT": 1500,
}
GRAPHENE_SCHEMAS_CACHE = {}

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
    "JWT_ALLOW_ANY_HANDLER": "bd_api.custom.graphql_jwt.allow_any",
}

# Translations
LANGUAGES = (
    ("pt", lambda x: "Português"),
    ("en", lambda x: "English"),
    ("es", lambda x: "Español"),
)
MODELTRANSLATION_AUTO_POPULATE = True

ALLOWED_UPLOAD_IMAGES = ["png"]

# Haystack
HAYSTACK_CONNECTIONS = {
    "default": {
        "ENGINE": "bd_api.apps.api.v1.haystack_engines.AsciifoldingElasticSearchEngine",
        "URL": getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200"),
        "TIMEOUT": 30,
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
HAYSTACK_SIGNAL_PROCESSOR = "bd_api.apps.api.v1.signals.BDSignalProcessor"

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

CSRF_COOKIE_HTTPONLY = False

DATA_UPLOAD_MAX_NUMBER_FIELDS = 20000

HUEY = {
    "name": "api.queue",
    "huey_class": "huey.RedisHuey",
    "results": True,
    "immediate": False,
    "connection": {
        "host": getenv("REDIS_HOST", "queue"),
        "port": getenv("REDIS_PORT", 6379),
        "db": getenv("REDIS_DB", 1),
        "read_timeout": 1,
        "connection_pool": None,
    },
    "consumer": {
        "workers": 2,
        "worker_type": "thread",
        "check_worker_health": True,
        "periodic": True,
    },
}
