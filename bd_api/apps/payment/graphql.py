# -*- coding: utf-8 -*-
from djstripe.models import Customer as DJStripeCustomer
from djstripe.models import Price as DJStripePrice
from djstripe.models import Subscription as DJStripeSubscription
from graphene import ID, Field, Float, InputObjectType, List, Mutation, ObjectType, String
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql_jwt.decorators import login_required
from loguru import logger
from stripe import Customer as StripeCustomer

from bd_api.apps.account.models import Account
from bd_api.custom.graphql_base import CountableConnection, PlainTextNode


class StripePriceNode(DjangoObjectType):
    product_name = String()
    amount = Float()

    class Meta:
        model = DJStripePrice
        fields = ("id",)
        filter_fields = ("id",)
        interfaces = (PlainTextNode,)
        connection_class = CountableConnection

    def resolve_product_name(root, info):
        return root.product.name

    def resolve_amount(root, info):
        return root.unit_amount / 100


class StripePriceQuery(ObjectType):
    stripe_price = PlainTextNode.Field(StripePriceNode)
    all_stripe_price = DjangoFilterConnectionField(StripePriceNode)


class StripeCustomerNode(DjangoObjectType):
    class Meta:
        model = DJStripeCustomer
        fields = ("id",)
        filter_fields = ("id",)
        interfaces = (PlainTextNode,)
        connection_class = CountableConnection


class StripeCustomerAddressInput(InputObjectType):
    line = String(required=True)
    city = String(required=True)
    state = String(required=True)
    country = String(required=True)
    postal_code = String(required=True)


class StripeCustomerInput(InputObjectType):
    name = String(required=True)
    email = String(required=True)
    address = StripeCustomerAddressInput(required=True)


class StripeCustomerCreateMutation(Mutation):
    """Create stripe customer
    - name
    - email
    - address
        - line: "Rua Augusta, 100"
        - city: "São Paulo"
        - state: "SP"
        - country: "BR"
        - postal_code: "01304-000"
    """

    customer = Field(StripeCustomerNode)
    errors = List(String)

    class Arguments:
        input = StripeCustomerInput()

    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        try:
            account = info.context.user
            account = Account.objects.get(id=account.id)
            customer = DJStripeCustomer.create(account)
            customer = StripeCustomer.modify(
                customer.id,
                {
                    "name": input.name,
                    "email": input.email,
                    "address": {
                        "city": input.address.city,
                        "line1": input.address.line,
                        "state": input.address.state,
                        "country": input.address.country,
                        "postal_code": input.address.postal_code,
                    },
                },
            )
            return cls(customer=customer)
        except Exception as e:
            logger.error(e)
            return cls(errors=[str(e)])


class StripeCustomerUpdateMutation(Mutation):
    """Update stripe customer
    - name
    - email
    - address
        - line1: "Rua Augusta, 100"
        - city: "São Paulo"
        - state: "SP"
        - country: "BR"
        - postal_code: "01304-000"
    """

    customer = Field(StripeCustomerNode)
    errors = String()

    class Arguments:
        input = StripeCustomerInput()

    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        try:
            account = info.context.user
            account = Account.objects.get(id=account.id)
            customer: DJStripeCustomer = account.djstripe_customers.first()
            customer = StripeCustomer.modify(
                customer.id,
                {
                    "name": input.name,
                    "email": input.email,
                    "address": {
                        "city": input.address.city,
                        "line1": input.address.line,
                        "state": input.address.state,
                        "country": input.address.country,
                        "postal_code": input.address.postal_code,
                    },
                },
            )
            return cls(customer=customer)
        except Exception as e:
            logger.error(e)
            return cls(errors=str(e))


class StripeCustomerMutation(ObjectType):
    create_stripe_customer = StripeCustomerCreateMutation.Field()
    update_stripe_customer = StripeCustomerUpdateMutation.Field()


class StripeSubscriptionNode(DjangoObjectType):
    client_secret = String()

    class Meta:
        model = DJStripeSubscription
        fields = ("id",)
        filter_fields = ("id",)
        interfaces = (PlainTextNode,)
        connection_class = CountableConnection

    def resolve_client_secret(root, info):
        return root.latest_invoice.payment_intent.client_secret


class StripeSubscriptionCreateMutation(Mutation):
    """Create stripe subscription"""

    subscription = Field(StripeSubscriptionNode)
    errors = List(String)

    class Arguments:
        price_id = ID(required=True)

    @classmethod
    @login_required
    def mutate(cls, root, info, price_id):
        try:
            account = info.context.user
            account = Account.objects.get(id=account.id)
            customer: DJStripeCustomer = account.djstripe_customers[0]
            subscription: DJStripeSubscription = customer.subscribe(
                price=price_id,
                payment_behaviour="default_incomplete",
                payment_settings={"save_default_payment_method": "on_subscription"},
            )
            return cls(subscription=subscription)
        except Exception as e:
            logger.error(e)
            return cls(errors=[str(e)])


class StripeSubscriptionDeleteMutation(Mutation):
    """Delete stripe subscription"""

    subscription = Field(StripeSubscriptionNode)
    errors = List(String)

    class Arguments:
        subscription_id = ID(required=True)

    @classmethod
    @login_required
    def mutate(cls, root, info, subscription_id):
        try:
            subscription = DJStripeSubscription.objects.get(id=subscription_id)
            subscription = subscription.cancel()
            return None
        except Exception as e:
            logger.error(e)
            return cls(errors=[str(e)])


class StripeSubscriptionMutation(ObjectType):
    create_stripe_subscription = StripeSubscriptionCreateMutation.Field()
    delete_stripe_subscription = StripeSubscriptionDeleteMutation.Field()


# Reference
# https://stripe.com/docs/billing/subscriptions/build-subscriptions?ui=elementsf
