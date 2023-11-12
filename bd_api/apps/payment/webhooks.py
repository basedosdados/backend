# -*- coding: utf-8 -*-
from django.conf import settings
from djstripe import webhooks
from djstripe.models import Event
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from loguru import logger

from bd_api.apps.account.models import Account, Subscription

logger = logger.bind(codename="payment_webhook")


def get_credentials(scopes: list[str] = None, impersonate: str = None):
    """Get google credentials with scope or subject"""
    cred = Credentials.from_service_account_file(
        settings.GOOGLE_APPLICATION_CREDENTIALS,
    )
    if scopes:
        cred = cred.with_scopes(scopes)
    if impersonate:
        cred = cred.with_subject(impersonate)
    return cred


def get_service() -> Resource:
    """Get google directory service"""
    credentials = get_credentials(
        settings.GOOGLE_DIRECTORY_SCOPES,
        settings.GOOGLE_DIRECTORY_SUBJECT,
    )
    return build("admin", "directory_v1", credentials=credentials)


def add_user(email: str, group_key: str, role: str = "MEMBER"):
    """Add user to google group"""
    if not group_key:
        group_key = settings.GOOGLE_DIRECTORY_GROUP_KEY
    try:
        service = get_service()
        service.members().insert(
            groupKey=group_key,
            body={"email": email, "role": role},
        ).execute()
    except HttpError as e:
        if e.resp.status == 490:
            logger.warning(f"{email} already exists")
        else:
            logger.error(e)
            raise e


def remove_user(email: str, group_key: str) -> None:
    """Remove user from google group"""
    if not group_key:
        group_key = settings.GOOGLE_DIRECTORY_GROUP_KEY
    try:
        service = get_service()
        service.members().delete(
            groupKey=group_key,
            memberKey=email,
        ).execute()
    except Exception as e:
        logger.error(e)
        raise e


@webhooks.handler("customer.subscription.created")
def subscribe(event: Event, **kwargs):
    """Add customer to allowed google groups"""
    add_user(event.customer.email)
    admin = Account.objects.get(email=event.customer.email).first()
    Subscription.objects.create(admin=admin, is_active=True)


@webhooks.handler("customer.subscription.deleted")
def unsubscribe(event: Event, **kwargs):
    """Remove customer from allowed google groups"""
    remove_user(event.customer.email)
    admin = Account.objects.get(email=event.customer.email).first()
    admin.subscription.is_active = False
    admin.subscription.save()


# Reference
# https://developers.google.com/admin-sdk/directory/v1/guides/troubleshoot-error-codes
# https://developers.google.com/admin-sdk/reseller/v1/support/directory_api_common_errors
