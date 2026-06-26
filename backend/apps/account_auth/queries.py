# -*- coding: utf-8 -*-
import graphene
from graphql_jwt import exceptions

from backend.apps.account_auth.models import BackendToken
from backend.apps.account_auth.mutations import BackendTokenType, _bt_to_type


class BackendTokenQuery(graphene.ObjectType):
    list_backend_tokens = graphene.List(
        BackendTokenType,
        user_id=graphene.ID(required=False),
    )

    def resolve_list_backend_tokens(self, info, user_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise exceptions.PermissionDenied()

        if user_id is not None and user.is_staff:
            qs = BackendToken.objects.filter(user_id=user_id)
        else:
            qs = BackendToken.objects.filter(user=user)

        return [_bt_to_type(bt) for bt in qs]
