# -*- coding: utf-8 -*-
from backend.apps.account.graphql import AccountMutation
from backend.apps.account_payment.graphql import Mutation as PaymentMutation
from backend.apps.account_payment.graphql import Query as PaymentQuery
from backend.apps.api.v1.graphql import Query as APIQuery
from backend.apps.user_notifications.graphql import (
    DeactivateAllTableUpdateNotification,
    DeactivateTableUpdateNotification,
    TableUpdateNotification,
)
from backend.apps.user_notifications.graphql import Query as UserNotificationQuery
from backend.custom.graphql_auto import build_schema

schema = build_schema(
    applications=["account", "v1"],
    extra_queries=[APIQuery, PaymentQuery, UserNotificationQuery],
    extra_mutations=[
        AccountMutation,
        PaymentMutation,
        TableUpdateNotification,
        DeactivateTableUpdateNotification,
        DeactivateAllTableUpdateNotification,
    ],
)
