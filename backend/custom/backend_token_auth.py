# -*- coding: utf-8 -*-
import hashlib

from django.utils import timezone


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class BackendTokenAuthBackend:
    """Django authentication backend for BackendToken credentials.

    Called by BackendTokenMiddleware with token=<raw> kwarg.
    Returns (Account, BackendToken) on success, None on failure.
    Does not access request — that is the middleware's responsibility.
    """

    def authenticate(self, request, token: str = None):
        if not token or not token.startswith("bdtoken_"):
            return None

        from backend.apps.account_auth.models import BackendToken

        hashed = _hash_token(token)
        try:
            bt = BackendToken.objects.select_related("user").get(
                hashed_key=hashed,
                is_active=True,
            )
        except BackendToken.DoesNotExist:
            return None

        if bt.expires_at is not None and bt.expires_at <= timezone.now():
            return None

        return (bt.user, bt)

    def get_user(self, user_id):
        from backend.apps.account.models import Account

        try:
            return Account.objects.get(pk=user_id)
        except Account.DoesNotExist:
            return None
