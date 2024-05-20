# -*- coding: utf-8 -*-
from djstripe.models import Subscription as DJStripeSubscription
from huey.contrib.djhuey import db_task
from loguru import logger

from backend.apps.account.models import Account, Subscription


@db_task()
def sync_subscription_task():
    """Create internal subscriptions from stripe subscriptions

    1. Subscription already exists
    2. Admin already exists
    3. Email already exists
    """

    def parse_name(subscription):
        name = subscription.customer.name.title().split(" ", 1)
        if len(name) == 1:
            return name, ""
        if len(name) == 2:
            return name

    for subscription in DJStripeSubscription.objects.order_by("-created").all():
        admin = None
        is_active = subscription.status == "active"
        if getattr(subscription, "internal_subscription", None):
            continue
        if getattr(subscription.customer, "subscriber", None):
            admin = subscription.customer.subscriber
        if getattr(subscription.customer, "email", None):
            try:
                first_name, last_name = parse_name(subscription)
                admin = admin or Account.objects.filter(
                    email=subscription.customer.email,
                ).first()  # fmt: skip
                admin = admin or Account.objects.create(
                    is_active=True,
                    last_name=last_name,
                    first_name=first_name,
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
