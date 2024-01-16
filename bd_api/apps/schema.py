# -*- coding: utf-8 -*-
from bd_api.apps.account.graphql import AccountMutation
from bd_api.apps.payment.graphql import (
    StripeCustomerMutation,
    StripePriceQuery,
    StripeSubscriptionCustomerMutation,
    StripeSubscriptionMutation,
)
from bd_api.custom.graphql_auto import build_schema

schema = build_schema(
    applications=["account", "v1"],
    extra_queries=[
        StripePriceQuery,
    ],
    extra_mutations=[
        AccountMutation,
        StripeCustomerMutation,
        StripeSubscriptionMutation,
        StripeSubscriptionCustomerMutation,
    ],
)
