# -*- coding: utf-8 -*-
from bd_api.apps.account.graphql import AccountMutation
from bd_api.apps.account_payment.graphql import Mutation as PaymentMutation
from bd_api.apps.account_payment.graphql import Query as PaymentQuery
from bd_api.apps.api.v1.graphql import Query as APIQuery
from bd_api.custom.graphql_auto import build_schema

schema = build_schema(
    applications=["account", "v1"],
    extra_queries=[
        APIQuery,
        PaymentQuery,
    ],
    extra_mutations=[
        AccountMutation,
        PaymentMutation,
    ],
)
