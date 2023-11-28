# -*- coding: utf-8 -*-
from django.contrib.admin import ModelAdmin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from djstripe.models import Subscription as DJStripeSubscription
from huey.contrib.djhuey import task
from loguru import logger

from bd_api.apps.account.models import Account, Subscription
from bd_api.custom.logger import setup_logger
from bd_api.utils import is_remote

level = "INFO" if is_remote() else "DEBUG"
serialize = True if is_remote() else False
setup_logger(level=level, serialize=serialize)


@task()
def sync_subscription_task(
    modeladmin: ModelAdmin = None,
    request: HttpRequest = None,
    queryset: QuerySet = None,
):
    """Create internal subscriptions from stripe subscriptions

    1. Subscription already exists
    2. Admin already exists
    3. Email already exists
    """
    for subscription in DJStripeSubscription.objects.order_by("-created").all():
        admin = None
        if getattr(subscription, "internal_subscription", None):
            continue
        if getattr(subscription.customer, "subscriber", None):
            admin = subscription.customer.subscriber
        if getattr(subscription.customer, "email", None):
            try:
                admin = admin or Account.objects.filter(
                    email=subscription.customer.email,
                ).first()  # fmt: skip
                admin = admin or Account.objects.create(
                    is_active=True,
                    email=subscription.customer.email,
                    username=subscription.customer.email.split("@")[0],
                )
                subscription.customer.subscriber = admin
                subscription.customer.save()
            except Exception as error:
                logger.error(error)
        if admin and subscription:
            Subscription.objects.create(admin=admin, subscription=subscription)
