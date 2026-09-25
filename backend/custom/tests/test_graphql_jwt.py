# -*- coding: utf-8 -*-
"""Tests for the GraphQL authorization decorators.

owner_required and subscription_member are the authorization boundary for the
GraphQL API: they decide whether a caller may read or write a given account or
subscription. owner_required identifies the target by regex over the raw request
body, which is unusual enough to be worth pinning down precisely.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from graphql import GraphQLResolveInfo
from graphql_jwt import exceptions

from backend.custom.graphql_jwt import (
    anyone_required,
    jwt_payload_with_uuid,
    owner_required,
    subscription_member,
)


def make_context(*, body=b"{}", is_staff=False, is_superuser=False, authenticated=True, uid=None):
    return SimpleNamespace(
        body=body,
        _post={},
        user=SimpleNamespace(
            id=uid,
            is_staff=is_staff,
            is_superuser=is_superuser,
            is_authenticated=authenticated,
            is_anonymous=not authenticated,
        ),
    )


def resolver(root, info, **kwargs):
    return "resolved"


def resolve_info(context):
    """graphql_jwt's @context finds the info by isinstance, so it must be the real type."""
    info = MagicMock(spec=GraphQLResolveInfo)
    info.context = context
    return info


def call(decorated, context):
    return decorated(None, resolve_info(context))


# ---------------------------------------------------------------------------
# JWT payload
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_the_jwt_payload_carries_the_account_uuid():
    from backend.apps.account.models import Account

    account = Account.objects.create_user(
        email="john.doe@email.com",
        password="12345678",
        username="john.doe",
        first_name="John",
        last_name="Doe",
    )
    payload = jwt_payload_with_uuid(account)
    assert payload["uuid"] == str(account.uuid)
    assert "exp" in payload


# ---------------------------------------------------------------------------
# anyone_required
# ---------------------------------------------------------------------------


def test_anyone_required_is_a_passthrough():
    decorated = anyone_required(resolver)
    assert decorated(None, None) == "resolved"
    assert decorated.__name__ == "resolver"


# ---------------------------------------------------------------------------
# owner_required
# ---------------------------------------------------------------------------


def test_staff_may_act_on_anyone():
    decorated = owner_required()(resolver)
    body = b"mutation { updateAccount(input: {id: 999}) { id } }"
    assert call(decorated, make_context(is_staff=True, uid=1, body=body)) == "resolved"


def test_a_superuser_may_act_on_anyone():
    decorated = owner_required()(resolver)
    body = b"mutation { updateAccount(input: {id: 999}) { id } }"
    context = make_context(is_superuser=True, uid=1, body=body)
    assert call(decorated, context) == "resolved"


def test_a_user_may_act_on_their_own_record():
    decorated = owner_required()(resolver)
    body = b'mutation { updateAccount(input: {id: 42, firstName: "John"}) { id } }'
    assert call(decorated, make_context(uid=42, body=body)) == "resolved"


def test_a_user_may_not_act_on_someone_elses_record():
    decorated = owner_required()(resolver)
    body = b"mutation { updateAccount(input: {id: 99}) { id } }"
    with pytest.raises(exceptions.PermissionDenied):
        call(decorated, make_context(uid=42, body=body))


def test_a_user_may_not_act_on_an_unidentified_record():
    """With no id in the body there is nothing to match the caller against."""
    decorated = owner_required()(resolver)
    with pytest.raises(exceptions.PermissionDenied):
        call(decorated, make_context(uid=42, body=b"{}"))


def test_an_anonymous_caller_is_denied_by_default():
    decorated = owner_required()(resolver)
    with pytest.raises(exceptions.PermissionDenied):
        call(decorated, make_context(authenticated=False))


def test_an_anonymous_caller_may_create_when_allowed():
    """Registration: no id in the body means no existing record is targeted."""
    decorated = owner_required(allow_anonymous=True)(resolver)
    assert call(decorated, make_context(authenticated=False)) == "resolved"


def test_an_anonymous_caller_may_not_target_an_existing_record():
    decorated = owner_required(allow_anonymous=True)(resolver)
    body = b"mutation { updateAccount(input: {id: 42}) { id } }"
    with pytest.raises(exceptions.PermissionDenied):
        call(decorated, make_context(authenticated=False, body=body))


@pytest.mark.parametrize(
    "body",
    [
        b"mutation { x(id: 42) }",
        b'mutation { x(id: "42") }',
        b"mutation { x(ID: 42) }",  # the body is lowercased before matching
        b"{ account(id: 42) { email } }",
    ],
)
def test_the_id_is_found_in_graphql_argument_syntax(body):
    decorated = owner_required()(resolver)
    assert call(decorated, make_context(uid=42, body=body)) == "resolved"


@pytest.mark.parametrize("body", [b'{"id": 42}', b'{"id": "42"}', b"{'id':42}"])
def test_a_json_style_key_is_not_recognised_as_an_id(body):
    """The pattern needs `id:` followed by whitespace, so a quoted JSON key misses.

    Recorded because it is load-bearing: an unrecognised id means owner_required
    treats the request as targeting no record, which denies an authenticated
    caller and, with allow_anonymous, permits an anonymous one. GraphQL request
    bodies carry the query in GraphQL syntax, so the pattern matches in practice.
    """
    decorated = owner_required()(resolver)
    with pytest.raises(exceptions.PermissionDenied):
        call(decorated, make_context(uid=42, body=body))


def test_an_undecodable_body_falls_back_to_post_data():
    decorated = owner_required()(resolver)
    context = make_context(uid=42)
    context.body = MagicMock()
    context.body.decode.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "boom")
    context._post = {"query": "mutation { x(id: 42) }"}
    assert call(decorated, context) == "resolved"


def test_a_custom_exception_can_be_supplied():
    class Denied(Exception):
        pass

    decorated = owner_required(exc=Denied)(resolver)
    with pytest.raises(Denied):
        call(decorated, make_context(authenticated=False))


# ---------------------------------------------------------------------------
# subscription_member
# ---------------------------------------------------------------------------


class FakeQuerySet:
    """Records the filter it was asked for, so the branch taken is observable."""

    def __init__(self):
        self.filtered_with = None

    def filter(self, *args, **kwargs):
        self.filtered_with = (args, kwargs)
        return self


def subscription_resolver(root, info, **kwargs):
    return info.context.queryset


def call_subscription(decorated, context):
    context.queryset = FakeQuerySet()
    result = decorated(None, resolve_info(context))
    return context.queryset, result


def test_an_anonymous_caller_cannot_read_subscriptions():
    decorated = subscription_member()(subscription_resolver)
    with pytest.raises(exceptions.PermissionDenied):
        call_subscription(decorated, make_context(authenticated=False))


def test_staff_see_subscriptions_unfiltered():
    decorated = subscription_member()(subscription_resolver)
    queryset, _ = call_subscription(decorated, make_context(is_staff=True))
    assert queryset.filtered_with is None


def test_a_superuser_sees_subscriptions_unfiltered():
    decorated = subscription_member()(subscription_resolver)
    queryset, _ = call_subscription(decorated, make_context(is_superuser=True))
    assert queryset.filtered_with is None


def test_a_member_sees_subscriptions_they_own_or_belong_to():
    decorated = subscription_member()(subscription_resolver)
    queryset, _ = call_subscription(decorated, make_context(uid=42))
    assert queryset.filtered_with is not None
    args, kwargs = queryset.filtered_with
    assert args and not kwargs  # a Q object, covering both owner and member


def test_only_admin_narrows_to_the_owner():
    decorated = subscription_member(only_admin=True)(subscription_resolver)
    queryset, _ = call_subscription(decorated, make_context(uid=42))
    _, kwargs = queryset.filtered_with
    assert set(kwargs) == {"admin"}
