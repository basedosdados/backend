# -*- coding: utf-8 -*-
from django.conf import settings
from djstripe import webhooks
from djstripe.models import Event
from djstripe.models import Subscription as DJStripeSubscription
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from loguru import logger

from bd_api.apps.account.models import Subscription

logger = logger.bind(module="payment")


def get_subscription(event: Event) -> Subscription:
    """Get internal subscription model, mirror of stripe"""
    subscription = DJStripeSubscription.objects.get(id=event.data["object"]["id"])
    if hasattr(subscription, "internal_subscription"):
        return subscription.internal_subscription
    else:
        return Subscription.objects.create(
            subscription=subscription,
            admin=event.customer.subscriber,
        )


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


def add_user(email: str, group_key: str = None, role: str = "MEMBER"):
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


def remove_user(email: str, group_key: str = None) -> None:
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
    subscription = get_subscription(event)
    add_user(event.customer.email)
    subscription.is_active = True
    subscription.save()


@webhooks.handler("customer.subscription.deleted")
def unsubscribe(event: Event, **kwargs):
    """Remove customer from allowed google groups"""
    subscription = get_subscription(event)
    remove_user(event.customer.email)
    subscription.is_active = False
    subscription.save()


@webhooks.handler("customer.updated")
def update_customer(event: Event, **kwargs):
    """Propagate customer email update"""
    account = event.customer.subscriber
    if account.email != event.data["object"]["email"]:
        account.email = event.data["object"]["email"]
        account.save()


# Reference
# https://developers.google.com/admin-sdk/directory/v1/guides/troubleshoot-error-codes
# https://developers.google.com/admin-sdk/reseller/v1/support/directory_api_common_errors
