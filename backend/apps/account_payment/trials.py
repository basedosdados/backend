# -*- coding: utf-8 -*-
from __future__ import annotations

from djstripe.models import Subscription as DJStripeSubscription

from backend.apps.account.models import Account

IGNORED_SUBSCRIPTION_STATUSES = frozenset({"incomplete", "incomplete_expired"})


def djstripe_subscription_is_chatbot(dj_sub: DJStripeSubscription) -> bool:
    try:
        if getattr(dj_sub, "plan", None) and getattr(dj_sub.plan, "product", None):
            return dj_sub.plan.product.metadata.get("code", "") == "chatbot"
        if hasattr(dj_sub, "items") and dj_sub.items.first():
            item = dj_sub.items.first()
            if getattr(item, "price", None) and getattr(item.price, "product", None):
                return item.price.product.metadata.get("code", "") == "chatbot"
    except Exception:
        pass
    return False


def account_has_active_chatbot_stripe_subscription(
    account: Account,
    exclude_stripe_subscription_id: str | None = None,
) -> bool:
    qs = DJStripeSubscription.objects.filter(
        customer__subscriber=account,
        status__in=["active", "trialing"],
    )
    if exclude_stripe_subscription_id:
        qs = qs.exclude(id=exclude_stripe_subscription_id)
    return any(djstripe_subscription_is_chatbot(s) for s in qs.iterator(chunk_size=20))


def account_djstripe_subscriptions(account: Account):
    return DJStripeSubscription.objects.filter(customer__subscriber=account).exclude(
        status__in=IGNORED_SUBSCRIPTION_STATUSES
    )


def account_has_prior_non_chatbot_subscription(account: Account) -> bool:
    """True if the account ever had a BD Pro (non-chatbot) Stripe subscription."""
    return any(
        not djstripe_subscription_is_chatbot(s)
        for s in account_djstripe_subscriptions(account).iterator(chunk_size=20)
    )


def account_has_prior_chatbot_subscription(account: Account) -> bool:
    """True if the account ever had a chatbot Stripe subscription."""
    return any(
        djstripe_subscription_is_chatbot(s)
        for s in account_djstripe_subscriptions(account).iterator(chunk_size=20)
    )


def account_eligible_for_bdpro_stripe_trial(account: Account) -> bool:
    return not account_has_prior_non_chatbot_subscription(account)


def account_eligible_for_chatbot_stripe_trial(account: Account) -> bool:
    return not account_has_prior_chatbot_subscription(account)
