# -*- coding: utf-8 -*-
from django.contrib.admin import ModelAdmin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from djstripe.models import Subscription as DJStripeSubscription

from bd_api.apps.account.models import Account, Subscription
from bd_api.custom.logger import setup_task_logger

logger = setup_task_logger()


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
        is_active = subscription.status == "active"
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
            Subscription.objects.create(
                admin=admin,
                is_active=is_active,
                subscription=subscription,
            )
            logger.info(f"Create subscription for {admin}")
