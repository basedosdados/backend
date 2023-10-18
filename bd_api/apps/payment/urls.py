# -*- coding: utf-8 -*-
from django.urls import include, path

from bd_api.apps.payment.views import StripeCustomerView, StripeSubscriptionView

urlpatterns = [
    path("", include("djstripe.urls", namespace="payment")),
    path("customer/<account_id>/", StripeCustomerView, name="payment_customer"),
    path(
        "subscription/<account_id>/<price_id>/", StripeSubscriptionView, name="payment_subscription"
    ),
]
