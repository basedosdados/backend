# -*- coding: utf-8 -*-
"""Tests for trial eligibility and chatbot product detection.

djstripe_subscription_is_chatbot decides which entitlement a Stripe webhook
grants or revokes: chatbot access, or Google Group membership. It reads the
product `code` metadata down two different paths (plan.product, or the first
line item's price.product) and swallows every exception, so a wrong answer is
silent — the customer simply doesn't get what they paid for.

The Stripe objects are stubbed rather than built in the database: these
functions only ever reach for `plan.product.metadata` or `items.first()`, and
duck types make the shape being relied on explicit.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.apps.account_payment import trials
from backend.apps.account_payment.trials import (
    IGNORED_SUBSCRIPTION_STATUSES,
    account_eligible_for_bdpro_stripe_trial,
    account_eligible_for_chatbot_stripe_trial,
    account_has_prior_chatbot_subscription,
    account_has_prior_non_chatbot_subscription,
    djstripe_subscription_is_chatbot,
)


def product(code):
    return SimpleNamespace(metadata={"code": code})


def sub_with_plan(code):
    """A subscription whose product is reachable via plan.product."""
    return SimpleNamespace(plan=SimpleNamespace(product=product(code)))


def sub_with_item(code):
    """A subscription whose product is only reachable via its first line item."""
    return SimpleNamespace(
        plan=None,
        items=SimpleNamespace(
            first=lambda: SimpleNamespace(price=SimpleNamespace(product=product(code)))
        ),
    )


class FakeQuerySet:
    def __init__(self, items):
        self._items = items

    def iterator(self, chunk_size=None):
        return iter(self._items)


# ---------------------------------------------------------------------------
# Product detection
# ---------------------------------------------------------------------------


def test_plan_product_marks_a_chatbot_subscription():
    assert djstripe_subscription_is_chatbot(sub_with_plan("chatbot")) is True


def test_plan_product_marks_a_non_chatbot_subscription():
    assert djstripe_subscription_is_chatbot(sub_with_plan("bd_pro")) is False


def test_the_line_item_price_is_the_fallback_path():
    assert djstripe_subscription_is_chatbot(sub_with_item("chatbot")) is True
    assert djstripe_subscription_is_chatbot(sub_with_item("bd_pro")) is False


def test_the_match_is_exact_not_a_substring():
    """ "chatbot_annual" is a different product and must not match."""
    assert djstripe_subscription_is_chatbot(sub_with_plan("chatbot_annual")) is False
    assert djstripe_subscription_is_chatbot(sub_with_plan("Chatbot")) is False


def test_missing_metadata_is_not_a_chatbot():
    assert djstripe_subscription_is_chatbot(sub_with_plan("")) is False
    assert djstripe_subscription_is_chatbot(SimpleNamespace(plan=None, items=None)) is False


def test_a_broken_subscription_object_is_not_a_chatbot():
    """The helper swallows errors and answers False rather than raising."""

    class Exploding:
        @property
        def plan(self):
            raise RuntimeError("stripe is down")

    assert djstripe_subscription_is_chatbot(Exploding()) is False


def test_an_empty_item_list_is_not_a_chatbot():
    sub = SimpleNamespace(plan=None, items=SimpleNamespace(first=lambda: None))
    assert djstripe_subscription_is_chatbot(sub) is False


# ---------------------------------------------------------------------------
# Prior subscriptions and trial eligibility
# ---------------------------------------------------------------------------


@pytest.fixture(name="account")
def fixture_account(db):
    from backend.apps.account.models import Account

    return Account.objects.create_user(
        email="john.doe@email.com",
        password="12345678",
        username="john.doe",
        first_name="John",
        last_name="Doe",
    )


def with_subscriptions(*subs):
    return patch.object(trials, "account_djstripe_subscriptions", return_value=FakeQuerySet(subs))


@pytest.mark.django_db
def test_no_history_means_both_trials_are_available(account):
    with with_subscriptions():
        assert account_eligible_for_bdpro_stripe_trial(account) is True
        assert account_eligible_for_chatbot_stripe_trial(account) is True


@pytest.mark.django_db
def test_a_prior_bdpro_subscription_burns_only_the_bdpro_trial(account):
    with with_subscriptions(sub_with_plan("bd_pro")):
        assert account_has_prior_non_chatbot_subscription(account) is True
        assert account_has_prior_chatbot_subscription(account) is False
        assert account_eligible_for_bdpro_stripe_trial(account) is False
        assert account_eligible_for_chatbot_stripe_trial(account) is True


@pytest.mark.django_db
def test_a_prior_chatbot_subscription_burns_only_the_chatbot_trial(account):
    with with_subscriptions(sub_with_plan("chatbot")):
        assert account_has_prior_chatbot_subscription(account) is True
        assert account_has_prior_non_chatbot_subscription(account) is False
        assert account_eligible_for_chatbot_stripe_trial(account) is False
        assert account_eligible_for_bdpro_stripe_trial(account) is True


@pytest.mark.django_db
def test_a_history_of_both_burns_both_trials(account):
    with with_subscriptions(sub_with_plan("chatbot"), sub_with_plan("bd_pro")):
        assert account_eligible_for_bdpro_stripe_trial(account) is False
        assert account_eligible_for_chatbot_stripe_trial(account) is False


def test_incomplete_subscriptions_are_ignored_when_looking_at_history():
    """An abandoned checkout must not burn a trial."""
    assert IGNORED_SUBSCRIPTION_STATUSES == frozenset({"incomplete", "incomplete_expired"})
