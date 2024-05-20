# -*- coding: utf-8 -*-
from functools import wraps
from os import getenv

WORKER = getenv("WORKER", "aux")
API_URL = getenv("BASE_URL_API", "https://localhost:8080")
SETTINGS = getenv("DJANGO_SETTINGS_MODULE", "backend.settings")


def is_remote():
    """Check if it is remote environment"""
    if "remote" in SETTINGS and "basedosdados.org" in API_URL:
        return True
    return False


def is_main():
    """Check if it is main environment"""
    if "main" in WORKER:
        return True
    return False


def is_dev():
    """Check if it is remote development environment"""
    if is_remote() and "development" in API_URL:
        return True
    return False


def is_stg():
    """Check if it is remote staging environment"""
    if is_remote() and "staging" in API_URL:
        return True
    return False


def is_prd():
    """Check if it is remote production environment"""
    if is_remote() and not is_dev() and not is_stg():
        return True
    return False


def get_backend_url():
    """Get backend url by environment"""

    if is_prd():
        return "backend.basedosdados.org"
    if is_stg():
        return "staging.backend.basedosdados.org"
    if is_dev():
        return "development.backend.basedosdados.org"
    return "localhost:8080"


def get_frontend_url():
    """Get frontend url by environment"""

    if is_prd():
        return "basedosdados.org"
    if is_stg():
        return "staging.basedosdados.org"
    if is_dev():
        return "development.basedosdados.org"
    return "localhost:3000"


def production_task(func):
    """Decorator that avoids function call if it isn't production"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if is_prd() and is_main():
            return func(*args, **kwargs)

    return wrapper
