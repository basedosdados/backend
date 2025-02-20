# -*- coding: utf-8 -*-
from backend.apps.account.graphql import AccountMutation
from backend.apps.account_payment.graphql import Mutation as PaymentMutation
from backend.apps.account_payment.graphql import Query as PaymentQuery
from backend.apps.api.v1.graphql import Query as APIQuery
from backend.custom.graphql_auto import build_schema

schema = build_schema(
    applications=["account", "v1", "data_api"],
    extra_queries=[
        APIQuery,
        PaymentQuery,
    ],
    extra_mutations=[
        AccountMutation,
        PaymentMutation,
    ],
)
