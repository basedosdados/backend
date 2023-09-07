# -*- coding: utf-8 -*-
from os import getenv as _getenv


def getadmins():
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
