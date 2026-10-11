# -*- coding: utf-8 -*-
import hashlib
import os
from datetime import datetime

import graphene
from graphql_jwt import exceptions

from backend.apps.account_auth.models import SCOPE_CHOICES, STAFF_ONLY_SCOPES, BackendToken

# ---------------------------------------------------------------------------
# GraphQL types
# ---------------------------------------------------------------------------


class BackendTokenType(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    prefix = graphene.String()
    scopes = graphene.List(graphene.String)
    expires_at = graphene.DateTime()
    created_at = graphene.DateTime()
    last_used_at = graphene.DateTime()
    is_active = graphene.Boolean()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_raw_token() -> str:
    return "bdtoken_" + os.urandom(32).hex()


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _bt_to_type(bt: BackendToken) -> BackendTokenType:
    return BackendTokenType(
        id=bt.pk,
        name=bt.name,
        prefix=bt.prefix,
        scopes=bt.scopes,
        expires_at=bt.expires_at,
        created_at=bt.created_at,
        last_used_at=bt.last_used_at,
        is_active=bt.is_active,
    )


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


class CreateBackendToken(graphene.Mutation):
    """Create a new BackendToken. Returns the raw token once — store it securely."""

    class Arguments:
        name = graphene.String(required=True)
        scopes = graphene.List(graphene.String, required=True)
        expires_at = graphene.DateTime(required=False)

    raw_token = graphene.String()
    token = graphene.Field(BackendTokenType)

    def mutate(self, info, name: str, scopes: list, expires_at: datetime = None):
        user = info.context.user
        if not user.is_authenticated:
            raise exceptions.PermissionDenied()

        invalid_scopes = [s for s in scopes if s not in SCOPE_CHOICES]
        if invalid_scopes:
            raise ValueError(f"Invalid scopes: {invalid_scopes}")

        if not user.is_staff:
            forbidden = [s for s in scopes if s in STAFF_ONLY_SCOPES]
            if forbidden:
                raise exceptions.PermissionDenied()

        raw = _generate_raw_token()
        # prefix = first 8 hex chars of the random part (after "bdtoken_")
        prefix = raw[len("bdtoken_") : len("bdtoken_") + 8]
        hashed = _hash_token(raw)

        bt = BackendToken.objects.create(
            user=user,
            name=name,
            prefix=prefix,
            hashed_key=hashed,
            scopes=scopes,
            expires_at=expires_at,
        )

        return CreateBackendToken(raw_token=raw, token=_bt_to_type(bt))


class RevokeBackendToken(graphene.Mutation):
    """Set a BackendToken as inactive. Users can only revoke their own tokens;
    staff can revoke any token."""

    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        user = info.context.user
        if not user.is_authenticated:
            raise exceptions.PermissionDenied()

        qs = BackendToken.objects.filter(pk=id)
        if not user.is_staff:
            qs = qs.filter(user=user)

        updated = qs.update(is_active=False)
        if not updated:
            raise exceptions.PermissionDenied()

        return RevokeBackendToken(ok=True)


class BackendTokenMutation:
    create_backend_token = CreateBackendToken.Field()
    revoke_backend_token = RevokeBackendToken.Field()
