# -*- coding: utf-8 -*-
from json import loads
from pathlib import Path

from django.conf import settings
from google.cloud.bigquery import Client as GBQClient
from google.cloud.storage import Client as GCSClient
from google.oauth2.service_account import Credentials
from loguru import logger
from requests import post


def get_gcloud_credentials():
    """Get google cloud credentials"""
    creds_env = settings.GOOGLE_APPLICATION_CREDENTIALS
    try:
        creds_path = Path(creds_env)
        credentials = Credentials.from_service_account_file(creds_path)
    except (TypeError, ValueError):
        credentials_dict = loads(creds_env)
        credentials = Credentials.from_service_account_info(credentials_dict)
    return credentials


def get_gbq_client():
    """Get google big query client"""
    return GBQClient(credentials=get_gcloud_credentials())


def get_gcs_client():
    """Get google cloud storage client"""
    return GCSClient(credentials=get_gcloud_credentials())


def send_discord_message(message: str):
    """Send a message to a discord channel"""
    if url := settings.DISCORD_BACKEND_WEBHOOK_URL:
        message = message[:2000]
        response = post(url, data={"content": message})
        logger.debug(f"{response.status_code}: {response.text}")
