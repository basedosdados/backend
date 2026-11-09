# -*- coding: utf-8 -*-
"""Reactivate a `trialing`/`active` Stripe subscription with a scheduled cancellation.

Stripe calls are pinned to dj-stripe's API version for `sync_from_stripe_data`.
"""

from __future__ import annotations

import stripe
from djstripe.models import Subscription as DJStripeSubscription
from djstripe.settings import djstripe_settings
from loguru import logger

logger = logger.bind(module="payment")

REACTIVATE_ACTION = "reactivate"
REACTIVATABLE_STATUSES = frozenset({"trialing", "active"})


def retrieve_stripe_subscription(stripe_subscription_id: str):
    return stripe.Subscription.retrieve(
        stripe_subscription_id,
        stripe_version=djstripe_settings.STRIPE_API_VERSION,
    )


def has_scheduled_cancellation(stripe_subscription) -> bool:
    return bool(
        stripe_subscription.get("cancel_at") or stripe_subscription.get("cancel_at_period_end")
    )


def is_reactivatable(stripe_subscription) -> bool:
    return stripe_subscription.get(
        "status"
    ) in REACTIVATABLE_STATUSES and has_scheduled_cancellation(stripe_subscription)


def reactivate_stripe_subscription(
    stripe_subscription_id: str,
    *,
    payment_method: str | None = None,
    price_id: str | None = None,
    promotion_code: str | None = None,
    remove_cancellation: bool = True,
):
    """Remove the scheduled cancellation and apply card, price and coupon.

    Keeps the remaining trial days and never prorates. With
    `remove_cancellation=False`, only price and coupon are applied.

    Returns the updated subscription, or `None` if it is no longer reactivatable.
    """
    current = retrieve_stripe_subscription(stripe_subscription_id)
    if not is_reactivatable(current):
        logger.info(
            f"Assinatura {stripe_subscription_id} não é reativável "
            f"(status={current.get('status')}, cancel_at={current.get('cancel_at')}, "
            f"cancel_at_period_end={current.get('cancel_at_period_end')})"
        )
        return None

    params = {}
    if remove_cancellation:
        if current.get("cancel_at_period_end"):
            params["cancel_at_period_end"] = False
        else:
            # An empty string unsets `cancel_at` on Stripe.
            params["cancel_at"] = ""

    if payment_method:
        params["default_payment_method"] = payment_method

    if promotion_code:
        params["discounts"] = [{"promotion_code": promotion_code}]

    if price_id:
        item = current["items"]["data"][0]
        if item["price"]["id"] != price_id:
            params["items"] = [{"id": item["id"], "price": price_id}]
            if current.get("status") == "trialing" and current.get("trial_end"):
                params["trial_end"] = current["trial_end"]

    if not params:
        return current

    updated = stripe.Subscription.modify(
        stripe_subscription_id,
        proration_behavior="none",
        stripe_version=djstripe_settings.STRIPE_API_VERSION,
        **params,
    )
    DJStripeSubscription.sync_from_stripe_data(updated)
    logger.info(
        f"Assinatura {stripe_subscription_id} "
        f"{'reativada' if remove_cancellation else 'atualizada antes da reativação'}"
    )
    return updated
