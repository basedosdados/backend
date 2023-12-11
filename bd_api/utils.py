# -*- coding: utf-8 -*-
from functools import wraps
from os import getenv

API_URL = getenv("BASE_URL_API", "https://localhost:8080")
SETTINGS = getenv("DJANGO_SETTINGS_MODULE", "bd_api.settings")


def is_remote():
    """Check if it is remote environment"""
    if "remote" in SETTINGS and "basedosdados.org" in API_URL:
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


def production_only(func):
    """Decorator that avoids function call if it isn't production"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if is_prod():
            return func(*args, **kwargs)

    return wrapper
