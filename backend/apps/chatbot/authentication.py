# -*- coding: utf-8 -*-
from backend.apps.account.models import Account


def authentication_rule(user: Account) -> bool:
    if user is not None:
        return user.has_chatbot_access
    return False
