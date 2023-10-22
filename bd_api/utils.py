# -*- coding: utf-8 -*-
from os import getenv as _getenv

API_URL = _getenv("BASE_URL_API", "https://localhost:8080")
SETTINGS = _getenv("DJANGO_SETTINGS_MODULE", "bd_api.settings")


def getadmins():
    """Get admins from environment variable"""
    admins = getenv("ADMINS")
    if admins is None:
        return []
    return [admin.split(",") for admin in admins.split(";")]


def getenv(var, default=None):
    """Get environment variable or raise exception if not set"""
    value = _getenv(var, default)
    if value is None:
        raise ValueError(f"Environment variable {var} not set")
    return value


def is_remote():
    """Check if it is remote environment"""
    if "prod" in SETTINGS and "basedosdados.org" in API_URL:
        return True
    return False


def is_dev():
    """Check if it is remote development environment"""
    if is_remote() and "development" in API_URL:
        return True
    return False


def is_stag():
    """Check if it is remote staging environment"""
    if is_remote() and "staging" in API_URL:
        return True
    return False


def is_prod():
    """Check if it is remote production environment"""
    if is_remote() and not is_dev() and not is_stag():
        return True
    return False


def prod_task(func):
    """Decorator that avoids function call if it isn't production"""

    def wrapper(*args, **kwargs):
        if is_prod():
            return func(*args, **kwargs)

    return wrapper
