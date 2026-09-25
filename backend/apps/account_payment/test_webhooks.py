# -*- coding: utf-8 -*-
"""Tests for the Stripe webhook helpers.

These are the guards every subscription handler runs before it grants or revokes
anything: the customer/email precondition, the account lookup, product
resolution, and the admin protection in _set_account_chatbot_access. All of them
fail quietly by design — they log and return None or False rather than raise —
so without tests a regression looks exactly like a customer who never paid.

Stripe events are stubbed. The helpers only touch `event.customer.email`,
`event.type`, `event.id` and `event.data["object"]["id"]`, and a duck type makes
that surface explicit.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.apps.account.models import Account
from backend.apps.account_payment.webhooks import (
    WebhookContext,
    _normalize_plus,
    _set_account_chatbot_access,
    get_account_for_stripe_customer,
    get_product_slug,
    get_subscription,
    require_webhook_customer_context,
    subscription_product_is_chatbot,
)


def fake_event(email="john.doe@email.com", *, object_id="sub_123", type="customer.updated"):
    customer = SimpleNamespace(email=email) if email is not None else None
    return SimpleNamespace(
        customer=customer,
        type=type,
        id="evt_1",
        data={"object": {"id": object_id}},
    )


def product(code):
    return SimpleNamespace(metadata={"code": code})


@pytest.fixture(name="account")
def fixture_account():
    return Account.objects.create_user(
        email="john.doe@email.com",
        password="12345678",
        username="john.doe",
        first_name="John",
        last_name="Doe",
    )


# ---------------------------------------------------------------------------
# Email normalisation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("user@example.com", "user@example.com"),
        ("User@Example.com", "user@example.com"),
        ("  user@example.com  ", "user@example.com"),
        ("user+test@example.com", "user@example.com"),
        ("user+a+b@example.com", "user@example.com"),
        ("USER+Tag@Example.COM", "user@example.com"),
        ("user+@example.com", "user@example.com"),
    ],
)
def test_normalize_plus(raw, expected):
    assert _normalize_plus(raw) == expected


def test_normalize_plus_leaves_a_plus_in_the_domain_alone():
    """Only the local part is aliased; the domain is untouched."""
    assert _normalize_plus("user@ex+ample.com") == "user@ex+ample.com"


# ---------------------------------------------------------------------------
# The customer/email precondition
# ---------------------------------------------------------------------------


def test_context_is_built_for_an_event_with_a_customer_email():
    wc = require_webhook_customer_context(fake_event())
    assert isinstance(wc, WebhookContext)
    assert wc.customer_email == "john.doe@email.com"
    assert wc.event_context == "Webhook: customer.updated | Event ID: evt_1"
    assert wc.ctx == "[Webhook: customer.updated | Event ID: evt_1] "


def test_no_context_without_a_customer():
    assert require_webhook_customer_context(fake_event(email=None)) is None


def test_no_context_without_an_email():
    assert require_webhook_customer_context(fake_event(email="")) is None


def test_the_invalid_case_can_be_logged_on_request():
    with patch("backend.apps.account_payment.webhooks.logger") as logger:
        assert require_webhook_customer_context(fake_event(email=None), log_if_invalid=True) is None
        logger.warning.assert_called_once()


def test_the_invalid_case_is_silent_by_default():
    with patch("backend.apps.account_payment.webhooks.logger") as logger:
        require_webhook_customer_context(fake_event(email=None))
        logger.warning.assert_not_called()


# ---------------------------------------------------------------------------
# Account lookup
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_the_account_is_found_by_the_customer_email(account):
    assert get_account_for_stripe_customer(fake_event()) == account


@pytest.mark.django_db
def test_an_unknown_customer_email_yields_no_account(account):
    assert get_account_for_stripe_customer(fake_event(email="nobody@email.com")) is None


# ---------------------------------------------------------------------------
# Product resolution
# ---------------------------------------------------------------------------


def test_product_slug_comes_from_the_subscriptions_plan():
    subscription = SimpleNamespace(
        subscription=SimpleNamespace(plan=SimpleNamespace(product=product("chatbot")))
    )
    assert get_product_slug(subscription) == "chatbot"


def test_product_slug_falls_back_to_the_first_line_item():
    dj_sub = SimpleNamespace(
        plan=None,
        items=SimpleNamespace(
            first=lambda: SimpleNamespace(price=SimpleNamespace(product=product("bd_pro")))
        ),
    )
    assert get_product_slug(SimpleNamespace(subscription=dj_sub)) == "bd_pro"


def test_product_slug_is_empty_when_nothing_resolves():
    assert get_product_slug(None, None) == ""
    assert get_product_slug(SimpleNamespace(subscription=None), None) == ""


def test_product_slug_is_empty_rather_than_raising():
    class Exploding:
        @property
        def subscription(self):
            raise RuntimeError("stripe is down")

    assert get_product_slug(Exploding()) == ""


@pytest.mark.django_db
def test_product_slug_from_the_event_when_the_subscription_has_none():
    """With no internal subscription the event's own id is looked up instead."""
    event = fake_event(object_id="sub_abc")
    with patch("backend.apps.account_payment.webhooks.DJStripeSubscription") as dj_subscription:
        dj_subscription.objects.filter.return_value.first.return_value = SimpleNamespace(
            plan=SimpleNamespace(product=product("chatbot"))
        )
        assert get_product_slug(None, event) == "chatbot"
        dj_subscription.objects.filter.assert_called_once_with(id="sub_abc")


def test_subscription_product_is_chatbot_wraps_the_slug_check():
    chatbot = SimpleNamespace(
        subscription=SimpleNamespace(plan=SimpleNamespace(product=product("chatbot")))
    )
    bd_pro = SimpleNamespace(
        subscription=SimpleNamespace(plan=SimpleNamespace(product=product("bd_pro")))
    )
    assert subscription_product_is_chatbot(chatbot, None, "ctx") is True
    assert subscription_product_is_chatbot(bd_pro, None, "ctx") is False
    assert subscription_product_is_chatbot(None, None, "ctx") is False


# ---------------------------------------------------------------------------
# get_subscription
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_subscription_needs_an_object_id():
    event = fake_event()
    event.data = {"object": {}}
    assert get_subscription(event) is None


@pytest.mark.django_db
def test_get_subscription_returns_none_for_an_unknown_stripe_subscription():
    assert get_subscription(fake_event(object_id="sub_missing")) is None


# ---------------------------------------------------------------------------
# Chatbot access, and the admin guard
# ---------------------------------------------------------------------------


def context():
    return WebhookContext(
        event=fake_event(), event_context="ctx", ctx="[ctx] ", customer_email="john.doe@email.com"
    )


@pytest.mark.django_db
def test_chatbot_access_is_granted(account):
    _set_account_chatbot_access(account, True, context(), "granting")
    account.refresh_from_db()
    assert account.has_chatbot_access is True


@pytest.mark.django_db
def test_chatbot_access_is_revoked(account):
    account.has_chatbot_access = True
    account.save()
    _set_account_chatbot_access(account, False, context(), "revoking")
    account.refresh_from_db()
    assert account.has_chatbot_access is False


@pytest.mark.django_db
def test_an_admin_never_loses_chatbot_access_to_a_webhook(account):
    """A lapsed Stripe subscription must not lock a staff member out."""
    account.is_admin = True
    account.has_chatbot_access = True
    account.save()
    _set_account_chatbot_access(account, False, context(), "revoking")
    account.refresh_from_db()
    assert account.has_chatbot_access is True


@pytest.mark.django_db
def test_an_admin_can_still_be_granted_access(account):
    account.is_admin = True
    account.save()
    _set_account_chatbot_access(account, True, context(), "granting")
    account.refresh_from_db()
    assert account.has_chatbot_access is True
