# -*- coding: utf-8 -*-
from django.urls import include, path

from bd_api.apps.payment.views import (
    StripeCustomerSubscriptionView,
    StripeCustomerView,
    StripePriceView,
    StripeSubscriptionView,
)

urlpatterns = [
    path("", include("djstripe.urls", namespace="payment")),
    path("customer/", StripeCustomerView.as_view(), name="payment_customer"),
    path("customer/<account_id>/", StripeCustomerView.as_view(), name="payment_customer"),
    path(
        "customer/<account_id>/subscription/",
        StripeCustomerSubscriptionView.as_view(),
        name="payment_subscription",
    ),
    path(
        "customer/<account_id>/subscription/<subscription_id>",
        StripeCustomerSubscriptionView.as_view(),
        name="payment_subscription",
    ),
    path(
        "price/",
        StripePriceView.as_view(),
        name="payment_price",
    ),
    path(
        "subscription/",
        StripeSubscriptionView.as_view(),
        name="payment_subscription",
    ),
    path(
        "subscription/<subscription_id>/",
        StripeSubscriptionView.as_view(),
        name="payment_subscription",
    ),
]
