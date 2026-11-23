# -*- coding: utf-8 -*-
"""Audit of the BD Pro Google Group against the subscriptions in the database.

The Stripe webhooks add and remove people from the Google Group one event at a
time. When a call fails, or an event is lost, the group drifts from what the
database says. This module compares the two sides so the drift shows up
(and can be fixed) instead of being found by a user who lost access.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.conf import settings

from backend.apps.account.models import Account, Subscription
from backend.apps.account_payment.webhooks import _normalize_plus, add_user, get_service

ACTIVE_STRIPE_STATUSES = frozenset({"active", "trialing"})


@dataclass
class GoogleGroupAudit:
    """Result of comparing the Google Group with the database.

    Attributes:
        expected: Normalized emails that should be in the group.
        members: Normalized emails that are in the group.
        missing: Accounts with an active BD Pro subscription that aren't in
            the group, as `(email, account_id, subscription_id)`.
        extra: Group members without an active BD Pro subscription in the
            database. Some are expected (admins, manual additions).
        stale: Internal subscriptions marked active whose Stripe status isn't
            `active`/`trialing`, as `(admin email, subscription_id, status)`.
    """

    expected: set[str] = field(default_factory=set)
    members: set[str] = field(default_factory=set)
    missing: list[tuple[str, int, str]] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    stale: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.stale


def group_email(account: Account) -> str:
    """Email the webhooks use for an account in the Google Group."""
    return _normalize_plus(account.gcp_email or account.email)


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


def active_pro_subscriptions():
    return [
        s
        for s in Subscription.objects.filter(is_active=True)
        .select_related("admin", "subscription__plan__product")
        .prefetch_related("subscribers")
        if s.subscription and s.is_pro
    ]


def audit_google_group(group_key: str | None = None) -> GoogleGroupAudit:
    """Compare the Google Group with the active BD Pro subscriptions.

    Owners and members (BD Pro Empresas) of an active subscription are
    expected in the group, under `gcp_email` or `email`.
    """
    audit = GoogleGroupAudit(members=list_group_members(group_key))
    seen: set[str] = set()
    for subscription in active_pro_subscriptions():
        stripe_status = subscription.subscription.status
        if stripe_status not in ACTIVE_STRIPE_STATUSES:
            audit.stale.append((subscription.admin.email, subscription.id, stripe_status))

        for account in [subscription.admin, *subscription.subscribers.all()]:
            email = group_email(account)
            audit.expected.add(email)
            if email not in audit.members and email not in seen:
                audit.missing.append((email, account.id, str(subscription.id)))
            seen.add(email)

    admins = {group_email(a) for a in Account.objects.filter(is_admin=True)}
    audit.extra = sorted(audit.members - audit.expected - admins)
    audit.stale.sort()
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
