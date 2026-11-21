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
):
    """Remove the scheduled cancellation and apply card, price and coupon.

    Keeps the remaining trial days and never prorates.

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

    updated = stripe.Subscription.modify(
        stripe_subscription_id,
        proration_behavior="none",
        stripe_version=djstripe_settings.STRIPE_API_VERSION,
        **params,
    )
    DJStripeSubscription.sync_from_stripe_data(updated)
    logger.info(f"Assinatura {stripe_subscription_id} reativada")
    return updated


def promotion_code_rejection(promotion, customer_id: str) -> str | None:
    """Check the promotion code restrictions Stripe would only enforce on `modify`.

    Runs before the card is collected, so a coupon Stripe would refuse doesn't
    fail later in the webhook. Returns the error message, or `None` if valid.
    """
    if not promotion or not promotion.get("active"):
        return "Cupom inválido."

    coupon = promotion.get("coupon") or {}
    if not coupon.get("valid", True):
        return "Este cupom não está mais ativo."

    restrictions = promotion.get("restrictions") or {}
    allowed_customer = promotion.get("customer")
    if allowed_customer and allowed_customer != customer_id:
        return "Este cupom não está disponível para a sua conta."

    if restrictions.get("first_time_transaction") and customer_has_successful_payment(customer_id):
        return "Este cupom vale apenas para a primeira compra."

    return None


def customer_has_successful_payment(customer_id: str) -> bool:
    charges = stripe.Charge.list(customer=customer_id, limit=100)
    return any(charge.get("status") == "succeeded" for charge in charges.get("data", []))


GENERIC_ERROR = "Não foi possível continuar a assinatura. Tente novamente ou fale com o suporte."
COUPON_ERROR = "Este cupom não pode ser usado nesta assinatura."


def stripe_error_message(error: stripe.error.StripeError) -> str:
    """Translate a Stripe error into a message that can be shown to the user.

    Stripe messages are technical and in English, so they only go to the logs.
    """
    param = getattr(error, "param", None) or ""
    code = getattr(error, "code", None) or ""
    if param.startswith(("discounts", "promotion_code", "coupon")) or "coupon" in code:
        return COUPON_ERROR
    return GENERIC_ERROR
