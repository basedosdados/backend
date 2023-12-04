# -*- coding: utf-8 -*-
from json import loads
from pathlib import Path

from django.conf import settings
from google.oauth2.service_account import Credentials


def get_credentials():
    """Get google cloud credentials"""
    creds_env = settings.GOOGLE_APPLICATION_CREDENTIALS
    try:
        creds_path = Path(creds_env)
        credentials = Credentials.from_service_account_file(creds_path)
    except (TypeError, ValueError):
        credentials_dict = loads(creds_env)
        credentials = Credentials.from_service_account_info(credentials_dict)
    return credentials
