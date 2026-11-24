# -*- coding: utf-8 -*-
"""Audit of the BD Pro Google Group against Stripe and the database.

The Stripe webhooks add and remove people from the Google Group one event at a
time. When a call fails, or an event is lost, the group drifts from what Stripe
says. This module compares the sides so the drift shows up (and can be fixed)
instead of being found by a user who lost access.

Stripe is the source of truth, read from its API. The local dj-stripe copy
isn't enough: dj-stripe syncs the subscription inside the same transaction as
our webhook handler, so when the handler keeps failing until Stripe gives up
retrying, the local status is rolled back together with `is_active`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import stripe
from django.conf import settings
from djstripe.models import Customer as DJStripeCustomer
from djstripe.models import Product as DJStripeProduct
from djstripe.settings import djstripe_settings

from backend.apps.account.models import Account, Subscription
from backend.apps.account_payment.webhooks import _normalize_plus, add_user, get_service

ACTIVE_STRIPE_STATUSES = ("active", "trialing")


@dataclass(frozen=True)
class PaidStripeSubscription:
    """A BD Pro subscription that is `active`/`trialing` in Stripe."""

    id: str
    customer_id: str
    status: str


@dataclass
class GoogleGroupAudit:
    """Result of comparing the Google Group with Stripe and the database.

    Attributes:
        expected: Normalized emails that should be in the group.
        members: Normalized emails that are in the group.
        missing: Accounts with a paid BD Pro subscription in Stripe that
            aren't in the group, as `(email, account_id, subscription_id)`.
        extra: Group members without a paid BD Pro subscription. Some are
            expected (admins, manual additions).
        stale: Internal subscriptions marked active whose Stripe status isn't
            `active`/`trialing`, as `(admin email, subscription_id, status)`.
        inactive: Subscriptions paid in Stripe but with `is_active=False` in
            the database, as `(admin email, subscription_id, status)`.
        unlinked: Subscriptions paid in Stripe without an internal
            Subscription, as `(customer email or id, stripe_subscription_id)`.
    """

    expected: set[str] = field(default_factory=set)
    members: set[str] = field(default_factory=set)
    missing: list[tuple[str, int, str]] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    stale: list[tuple[str, str, str]] = field(default_factory=list)
    inactive: list[tuple[str, str, str]] = field(default_factory=list)
    unlinked: list[tuple[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.missing or self.stale or self.inactive or self.unlinked)


def group_email(account: Account) -> str:
    """Email the webhooks use for an account in the Google Group."""
    return _normalize_plus(account.gcp_email or account.email)


def _stripe_options() -> dict:
    return {
        "api_key": djstripe_settings.STRIPE_SECRET_KEY,
        "stripe_version": djstripe_settings.STRIPE_API_VERSION,
    }


def list_group_members(group_key: str | None = None) -> set[str]:
    """List every member of the Google Group, following pagination.

    Raises:
        google.auth.exceptions.RefreshError: If the service account key or its
            domain-wide delegation is no longer valid.
        googleapiclient.errors.HttpError: On any other API failure.
    """
    group_key = group_key or settings.GOOGLE_DIRECTORY_GROUP_KEY
    service = get_service()
    members: set[str] = set()
    page_token = None
    while True:
        response = (
            service.members()
            .list(groupKey=group_key, maxResults=200, pageToken=page_token)
            .execute()
        )
        for member in response.get("members", []):
            if email := member.get("email"):
                members.add(_normalize_plus(email))
        page_token = response.get("nextPageToken")
        if not page_token:
            return members


def _is_pro_product(product_id: str, known: dict[str, bool]) -> bool:
    """Whether a Stripe product is BD Pro (`bd_pro` or `bd_pro_empresas`)."""
    if product_id not in known:
        product = DJStripeProduct.objects.filter(id=product_id).first()
        if product:
            metadata = product.metadata or {}
        else:
            metadata = stripe.Product.retrieve(product_id, **_stripe_options()).get("metadata")
        known[product_id] = "bd_pro" in ((metadata or {}).get("code") or "")
    return known[product_id]


def _object_id(value) -> str:
    return value if isinstance(value, str) else value["id"]


def paid_pro_subscriptions_in_stripe() -> list[PaidStripeSubscription]:
    """List the BD Pro subscriptions that are `active`/`trialing` in Stripe.

    A subscription canceled at period end stays `active` until the period it
    paid for ends, so it's listed until then.
    """
    products: dict[str, bool] = {}
    paid = []
    for status in ACTIVE_STRIPE_STATUSES:
        subscriptions = stripe.Subscription.list(status=status, limit=100, **_stripe_options())
        for subscription in subscriptions.auto_paging_iter():
            items = (subscription.get("items") or {}).get("data") or []
            product_ids = {_object_id(item["price"]["product"]) for item in items}
            if any(_is_pro_product(product_id, products) for product_id in product_ids):
                paid.append(
                    PaidStripeSubscription(
                        id=subscription["id"],
                        customer_id=_object_id(subscription["customer"]),
                        status=status,
                    )
                )
    return paid


def internal_subscriptions(stripe_ids: set[str]) -> dict[str, Subscription]:
    """Internal Subscriptions for the given Stripe subscription ids."""
    subscriptions = (
        Subscription.objects.filter(subscription__id__in=stripe_ids)
        .select_related("admin", "subscription")
        .prefetch_related("subscribers")
    )
    return {s.subscription.id: s for s in subscriptions}


def active_pro_subscriptions():
    return [
        s
        for s in Subscription.objects.filter(is_active=True)
        .select_related("admin", "subscription__plan__product")
        .prefetch_related("subscribers")
        if s.subscription and s.is_pro
    ]


def stripe_status(subscription: Subscription) -> str:
    """Current Stripe status of a subscription, read from the API.

    Falls back to the local dj-stripe status if the API call fails.
    """
    try:
        return stripe.Subscription.retrieve(subscription.subscription.id, **_stripe_options())[
            "status"
        ]
    except stripe.error.StripeError:
        return subscription.subscription.status


def customer_account(customer_id: str) -> tuple[Account | None, str]:
    """Find the account of a Stripe customer.

    Returns:
        `(account or None, label)`, where `label` is the customer email (or
        id, when Stripe has no email) to show in the report.
    """
    customer = DJStripeCustomer.objects.filter(id=customer_id).first()
    if customer and customer.subscriber:
        return customer.subscriber, customer.subscriber.email
    if customer:
        email = customer.email
    else:
        email = stripe.Customer.retrieve(customer_id, **_stripe_options()).get("email")
    email = (email or "").strip()
    account = Account.objects.filter(email__iexact=email).first() if email else None
    return account, email or customer_id


def audit_google_group(group_key: str | None = None) -> GoogleGroupAudit:
    """Compare the Google Group with the BD Pro subscriptions paid in Stripe.

    Owners and members (BD Pro Empresas) of a paid subscription are expected
    in the group, under `gcp_email` or `email`, whatever `is_active` says in
    the database. Mismatches between Stripe and the database are reported in
    `stale`, `inactive` and `unlinked`.
    """
    audit = GoogleGroupAudit(members=list_group_members(group_key))
    paid = paid_pro_subscriptions_in_stripe()
    paid_ids = {p.id for p in paid}
    internal = internal_subscriptions(paid_ids)
    seen: set[str] = set()

    def expect(account: Account, subscription_id: str):
        email = group_email(account)
        audit.expected.add(email)
        if email not in audit.members and email not in seen:
            audit.missing.append((email, account.id, subscription_id))
        seen.add(email)

    for paid_subscription in paid:
        subscription = internal.get(paid_subscription.id)
        if subscription is None:
            account, label = customer_account(paid_subscription.customer_id)
            audit.unlinked.append((label, paid_subscription.id))
            if account:
                expect(account, paid_subscription.id)
            continue

        if not subscription.is_active:
            audit.inactive.append(
                (subscription.admin.email, str(subscription.id), paid_subscription.status)
            )
        for account in [subscription.admin, *subscription.subscribers.all()]:
            expect(account, str(subscription.id))

    for subscription in active_pro_subscriptions():
        if subscription.subscription.id not in paid_ids:
            audit.stale.append(
                (subscription.admin.email, str(subscription.id), stripe_status(subscription))
            )

    admins = {group_email(a) for a in Account.objects.filter(is_admin=True)}
    audit.extra = sorted(audit.members - audit.expected - admins)
    audit.stale.sort()
    audit.inactive.sort()
    audit.unlinked.sort()
    return audit


def add_missing_members(audit: GoogleGroupAudit) -> list[tuple[str, str]]:
    """Add the missing accounts to the group.

    Returns:
        `(email, error)` for each account that couldn't be added.
    """
    failures = []
    accounts = Account.objects.in_bulk([account_id for _, account_id, _ in audit.missing])
    for email, account_id, _ in audit.missing:
        try:
            add_user(email, account=accounts.get(account_id), event_context="google_group_audit")
        except Exception as e:
            failures.append((email, str(e)))
    return failures
