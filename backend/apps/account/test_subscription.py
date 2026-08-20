# -*- coding: utf-8 -*-
"""Tests for the subscription properties on Account and Subscription.

These decide what a paying user can reach: pro_subscription_status is read by the
frontend and by CustomVerify to gate BD Pro features, and owner/member precedence
determines whose plan applies when a user is both. The Stripe side is stubbed —
the branch logic here is what breaks, not dj-stripe.
"""

from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

import pytest

from backend.apps.account.models import Account, Subscription


def stripe_sub(code="bd_pro", *, slots="5", status="active"):
    """A stand-in for an internal Subscription with a Stripe plan behind it."""
    return SimpleNamespace(
        stripe_subscription=code,
        stripe_subscription_slots=slots,
        stripe_subscription_status=status,
        is_pro="bd_pro" in code,
    )


def as_owner(sub):
    return patch.object(Account, "pro_owner_subscription", PropertyMock(return_value=sub))


def as_member(sub):
    return patch.object(Account, "pro_member_subscription", PropertyMock(return_value=sub))


@pytest.fixture(name="account")
def fixture_account():
    return Account.objects.create_user(
        email="john.doe@email.com",
        password="12345678",
        username="john.doe",
        first_name="John",
        last_name="Doe",
    )


@pytest.fixture(name="member")
def fixture_member():
    return Account.objects.create_user(
        email="jane.roe@email.com",
        password="12345678",
        username="jane.roe",
        first_name="Jane",
        last_name="Roe",
    )


# ---------------------------------------------------------------------------
# No subscription
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_an_account_without_a_subscription_reports_nothing(account):
    assert account.pro_owner_subscription is None
    assert account.pro_member_subscription is None
    assert account.pro_subscription is None
    assert account.pro_subscription_role is None
    assert account.pro_subscription_slots is None
    assert account.pro_subscription_status is None
    assert account.is_subscriber is False


# ---------------------------------------------------------------------------
# Owner and member
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_an_owner_reports_their_own_plan(account):
    with as_owner(stripe_sub("bd_pro", slots="5")), as_member(None):
        assert account.pro_subscription == "bd_pro"
        assert account.pro_subscription_role == "owner"
        assert account.pro_subscription_slots == "5"
        assert account.is_subscriber is True


@pytest.mark.django_db
def test_a_member_reports_the_plan_they_belong_to(account):
    with as_owner(None), as_member(stripe_sub("bd_pro_empresas", slots="20")):
        assert account.pro_subscription == "bd_pro_empresas"
        assert account.pro_subscription_role == "member"
        assert account.pro_subscription_slots == "20"
        assert account.is_subscriber is True


@pytest.mark.django_db
def test_being_an_owner_takes_precedence_over_being_a_member(account):
    """Someone who owns one plan and belongs to another reports the one they own."""
    with (
        as_owner(stripe_sub("bd_pro", slots="5")),
        as_member(stripe_sub("bd_pro_empresas", slots="20")),
    ):
        assert account.pro_subscription == "bd_pro"
        assert account.pro_subscription_role == "owner"
        assert account.pro_subscription_slots == "5"


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_trial_reads_as_active(account):
    """The frontend gates on "active"; a trialing customer has paid-tier access."""
    with as_owner(stripe_sub(status="trialing")), as_member(None):
        assert account.pro_subscription_status == "active"


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["active", "past_due", "canceled", "unpaid", "paused"])
def test_every_other_status_passes_through(account, status):
    with as_owner(stripe_sub(status=status)), as_member(None):
        assert account.pro_subscription_status == status


@pytest.mark.django_db
def test_a_members_trial_is_converted_too(account):
    with as_owner(None), as_member(stripe_sub(status="trialing")):
        assert account.pro_subscription_status == "active"


# ---------------------------------------------------------------------------
# Which internal subscriptions count
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_an_inactive_internal_subscription_is_not_a_pro_subscription(account):
    Subscription.objects.create(admin=account, is_active=False)
    assert account.pro_owner_subscription is None


@pytest.mark.django_db
def test_a_subscription_without_a_stripe_plan_is_not_pro(account):
    """is_pro reads the Stripe product metadata, so a detached row cannot qualify."""
    Subscription.objects.create(admin=account, is_active=True)
    with pytest.raises(AttributeError):
        _ = account.pro_owner_subscription


# ---------------------------------------------------------------------------
# Subscription membership
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_the_admin_is_listed_first_and_labelled(account):
    subscription = Subscription.objects.create(admin=account, is_active=True)
    assert subscription.subscribers_info == [{"email": "john.doe@email.com", "role": "admin"}]


@pytest.mark.django_db
def test_members_are_listed_after_the_admin(account, member):
    subscription = Subscription.objects.create(admin=account, is_active=True)
    subscription.subscribers.add(member)
    assert subscription.subscribers_info == [
        {"email": "john.doe@email.com", "role": "admin"},
        {"email": "jane.roe@email.com", "role": "subscriber"},
    ]


@pytest.mark.django_db
def test_the_admin_email_falls_back_to_a_placeholder(account):
    subscription = Subscription.objects.create(admin=account, is_active=True)
    assert subscription.admin_email == "john.doe@email.com"
    account.email = ""
    assert subscription.admin_email == "test@stripe.com"


@pytest.mark.django_db
def test_stripe_derived_dates_are_none_without_a_stripe_subscription(account):
    subscription = Subscription.objects.create(admin=account, is_active=True)
    assert subscription.canceled_at is None
    assert subscription.plan_interval is None
    assert subscription.next_billing_cycle is None


# ---------------------------------------------------------------------------
# Staff
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_is_staff_tracks_is_admin(account):
    assert account.is_staff is False
    account.is_admin = True
    assert account.is_staff is True


@pytest.mark.django_db
def test_the_customer_is_the_first_linked_stripe_customer(account):
    assert account.customer is None
