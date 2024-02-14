# -*- coding: utf-8 -*-
from json import loads
from pathlib import Path
from typing import Any

from django.conf import settings
from google.cloud.bigquery import Client as GBQClient
from google.cloud.storage import Client as GCSClient
from google.oauth2.service_account import Credentials
from loguru import logger
from requests import post

from bd_api.custom.model import BaseModel


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


class Messenger:
    _length: int
    _message: str
    _soft_limit: int = 1600
    _hard_limit: int = 2000

    @property
    def length(self) -> int:
        return len(self._message)

    @property
    def is_full(self) -> bool:
        return len(self._message) >= self._soft_limit

    def __init__(self, header: str):
        self._message = f"{header.strip()}  "

    def append(self, entity: BaseModel = None, text: Any = None):
        """Append line if message length is less than limit"""
        if entity and text:
            line = f"\n- [{entity}]({entity.admin_url}): `{text}`"
            if len(self._message) + len(line) <= self._hard_limit:
                self._message += line
                return self._message

    def send(self):
        """Send message if it has body text"""
        if self._message.count("\n"):
            send_discord_message(self._message)
