# -*- coding: utf-8 -*-
from functools import wraps
from re import findall

from graphql_jwt import exceptions
from graphql_jwt.compat import get_operation_name
from graphql_jwt.decorators import context
from graphql_jwt.settings import jwt_settings


def allow_any(info, **kwargs):
    """Custom function to determine the non-authentication per-field

    References:
    - https://django-graphql-jwt.domake.io/settings.html#jwt-allow-any-handler
    """
    try:
        operation_name = get_operation_name(info.operation.operation).title()
        operation_type = info.schema.get_type(operation_name)
        if hasattr(operation_type, "fields"):
            field = operation_type.fields.get(info.field_name)
            if field is None:
                return False
        else:
            return False
        graphene_type = getattr(field.type, "graphene_type", None)
        return graphene_type is not None and issubclass(
            graphene_type, tuple(jwt_settings.JWT_ALLOW_ANY_CLASSES)
        )
    except Exception:
        return False


def ownership_required(f, exc=exceptions.PermissionDenied):
    """Custom decorator to limit graphql account mutations

    - Superusers are allowed to edit accounts
    - Anonymous users are allowed to create accounts
    - Authenticated users are allowed to edit their own account

    References:
    - https://django-graphql-jwt.domake.io/decorators.html
    """

    def get_uid(context, exp=r"id:\s[\"]?(\d+)[\"]?"):
        try:
            query = context.body.decode("utf-8").replace('\\"', "").lower()
        except Exception:
            query = str(context._post).replace('\\"', "").lower()

        return [int(uid) for uid in findall(exp, query)]

    @wraps(f)
    @context(f)
    def wrapper(context, *args, **kwargs):
        if context.user.is_superuser:
            return f(*args, **kwargs)
        uid = get_uid(context)
        if context.user.is_anonymous:
            if not uid:
                return f(*args, **kwargs)
        if context.user.is_authenticated:
            if context.user.id == uid[0]:
                return f(*args, **kwargs)

        raise exc

    return wrapper
