from backend.apps.account.models import Account


def authentication_rule(user: Account) -> bool:
    return user.has_chatbot_access
