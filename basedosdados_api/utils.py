# -*- coding: utf-8 -*-
from os import getenv as _getenv

from django.conf import settings

DB_NAME = settings.DATABASES.get("default", {}).get("NAME", "")
DB_ENGINE = settings.DATABASES.get("default", {}).get("ENGINE", "")


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
    return "prod" in settings.SETTINGS_MODULE


def is_dev():
    """Check if it is remote development environment"""
    if is_remote() and "dev" in DB_NAME:
        return True
    return False


def is_stag():
    """Check if it is remote staging environment"""
    if is_remote() and "stag" in DB_NAME:
        return True
    return False


def is_prod():
    """Check if it is remote production environment"""
    if is_remote() and not is_dev() and not is_stag():
        return True
    return False
