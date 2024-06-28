# -*- coding: utf-8 -*-
from functools import wraps
from re import findall

from django.db.models import Q
from graphene import Field, ObjectType, String
from graphql_jwt import exceptions
from graphql_jwt.compat import get_operation_name
from graphql_jwt.decorators import context
from graphql_jwt.relay import JSONWebTokenMutation
from graphql_jwt.settings import jwt_settings


class User(ObjectType):
    id = String()
    email = String()


class ObtainJSONWebTokenWithUser(JSONWebTokenMutation):
    user = Field(User)

    @classmethod
    def resolve(cls, root, info, **kwargs):
        return cls(user=info.context.user)


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


def anyone_required(f):
    """Decorator to open graphql queries and mutations"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper


def owner_required(allow_anonymous=False, exc=exceptions.PermissionDenied):
    """Decorator to limit graphql queries and mutations

    - Super users are allowed to edit all resources
    - Staff users are allowed to edit all resources
    - Anonymous users are allowed to create resources
    - Authenticated users are allowed to edit their own resources

    References:
    - https://django-graphql-jwt.domake.io/decorators.html
    """

    def get_uid(context, exp=r"id:\s[\"]?(\d+)[\"]?"):
        try:
            query = context.body.decode("utf-8").replace('\\"', "").lower()
        except Exception:
            query = str(context._post).replace('\\"', "").lower()
        uid = [int(uid) for uid in findall(exp, query)]
        return uid[0] if uid else None

    def decorator(f):
        @wraps(f)
        @context(f)
        def wrapper(context, *args, **kwargs):
            if context.user.is_staff:
                return f(*args, **kwargs)
            if context.user.is_superuser:
                return f(*args, **kwargs)
            uid = get_uid(context)
            if context.user.is_authenticated:
                if context.user.id == uid:
                    return f(*args, **kwargs)
            if context.user.is_anonymous:
                if allow_anonymous and not uid:
                    return f(*args, **kwargs)
            raise exc

        return wrapper

    return decorator


def subscription_member(only_admin=False, exc=exceptions.PermissionDenied):
    """Decorator to limit graphql queries and mutations

    - Super users are allowed to edit all resources
    - Staff users are allowed to edit all resources
    - If only_admin is True, only the admin(subscription owner) can edit/view the resource
    - Authenticated users are allowed to edit/view their own subscriptions

    References:
    - https://django-graphql-jwt.domake.io/decorators.html
    """

    def decorator(f):
        @wraps(f)
        @context(f)
        def wrapper(context, *args, **kwargs):
            if not context.user.is_authenticated:
                raise exc

            if context.user.is_staff or context.user.is_superuser:
                return f(*args, **kwargs)

            subscriptions = f(*args, **kwargs)

            if only_admin:
                subscriptions = subscriptions.filter(admin=context.user)
            else:
                subscriptions = subscriptions.filter(
                    Q(subscribers=context.user) | Q(admin=context.user)
                )

            return subscriptions

        return wrapper

    return decorator
