# -*- coding: utf-8 -*-
from django.contrib.admin import ModelAdmin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from djstripe.models import Subscription as DJStripeSubscription
from huey.contrib.djhuey import task

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
    """Create internal subscriptions from stripe subscriptions"""
    for subscription in DJStripeSubscription.objects.all():
        if hasattr(subscription, "internal_subscription"):
            return
        if hasattr(subscription.customer, "subscriber"):
            admin = subscription.customer.subscriber
        else:
            admin = None
            admin = admin or Account.objects.filter(
                email=subscription.customer.email,
            ).first()  # fmt: skip
            admin = admin or Account.objects.create(
                email=subscription.customer.email,
                username=subscription.customer.email.split("@")[0],
            )
            subscription.customer.subscriber = admin
            subscription.customer.save()
        Subscription.objects.create(admin=admin, subscription=subscription)
