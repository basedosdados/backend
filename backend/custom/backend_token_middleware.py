# -*- coding: utf-8 -*-
from graphql_jwt import exceptions

from backend.custom.backend_token_auth import BackendTokenAuthBackend

_backend = BackendTokenAuthBackend()


class BackendTokenMiddleware:
    """Graphene middleware that authenticates requests carrying an
    'Authorization: Token bdtoken_...' header.

    Runs after graphql_jwt.middleware.JSONWebTokenMiddleware. If the header
    uses the 'Bearer' prefix (JWT) or is absent, this middleware does nothing.
    On success: sets request.user and request._backend_token, updates last_used_at.
    On failure (bad/expired token): raises PermissionDenied.
    """

    def resolve(self, next_, root, info, **kwargs):
        request = info.context
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if auth_header.startswith("Token "):
            raw = auth_header[len("Token ") :]
            result = _backend.authenticate(request, token=raw)

            if result is None:
                raise exceptions.PermissionDenied()

            user, backend_token = result
            request.user = user
            request._backend_token = backend_token

            # Update last_used_at without triggering full model validation
            from django.utils import timezone

            type(backend_token).objects.filter(pk=backend_token.pk).update(
                last_used_at=timezone.now()
            )

        return next_(root, info, **kwargs)
