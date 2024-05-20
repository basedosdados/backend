# -*- coding: utf-8 -*-
import stripe
from django.conf import settings
from djstripe.models import Customer as DJStripeCustomer
from djstripe.models import Price as DJStripePrice
from djstripe.models import Subscription as DJStripeSubscription
from graphene import ID, Boolean, Field, Float, InputObjectType, List, Mutation, ObjectType, String
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql_jwt.decorators import login_required
from loguru import logger
from stripe import Customer as StripeCustomer

from bd_api.apps.account.models import Account, Subscription
from bd_api.apps.account_payment.webhooks import add_user, remove_user
from bd_api.custom.graphql_base import CountableConnection, PlainTextNode

if settings.STRIPE_LIVE_MODE:
    stripe.api_key = settings.STRIPE_LIVE_SECRET_KEY
else:
    stripe.api_key = settings.STRIPE_TEST_SECRET_KEY


class StripePriceNode(DjangoObjectType):
    _id = ID(name="_id")
    amount = Float()
    product_name = String()
    product_slug = String()
    product_slots = String()

    class Meta:
        model = DJStripePrice
        fields = ("id",)
        filter_fields = ("id",)
        interfaces = (PlainTextNode,)
        connection_class = CountableConnection

    def resolve__id(root, info):
        return root.djstripe_id

    def resolve_amount(root, info):
        return root.unit_amount / 100

    def resolve_product_name(root, info):
        return root.product.name

    def resolve_product_slug(root, info):
        return root.product.metadata.get("code", "")

    def resolve_product_slots(root, info):
        return root.product.metadata.get("slots", "0")


class StripeCustomerNode(DjangoObjectType):
    class Meta:
        model = DJStripeCustomer
        fields = ("id",)
        filter_fields = ("id",)
        interfaces = (PlainTextNode,)
        connection_class = CountableConnection


class StripeCustomerAddressInput(InputObjectType):
    line = String()
    city = String()
    state = String()
    country = String()
    postal_code = String()


class StripeCustomerInput(InputObjectType):
    name = String(required=True)
    email = String(required=True)
    address = StripeCustomerAddressInput()


class StripeCustomerCreateMutation(Mutation):
    """Create stripe customer"""

    customer = Field(StripeCustomerNode)
    errors = List(String)

    class Arguments:
        input = StripeCustomerInput()

    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        try:
            admin = info.context.user
            if customer := admin.customer:
                ...
            else:
                customer = DJStripeCustomer.create(admin)
                parameters = {
                    "name": input.name,
                    "email": input.email,
                }
                if input.address:
                    parameters["address"] = {
                        "city": input.address.city,
                        "line1": input.address.line,
                        "state": input.address.state,
                        "country": input.address.country,
                        "postal_code": input.address.postal_code,
                    }
                StripeCustomer.modify(
                    customer.id,
                    **parameters,
                )
            return cls(customer=customer)
        except Exception as e:
            logger.error(e)
            return cls(errors=[str(e)])


class StripeCustomerUpdateMutation(Mutation):
    """Update stripe customer"""

    customer = Field(StripeCustomerNode)
    errors = String()

    class Arguments:
        input = StripeCustomerInput()

    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        try:
            account = info.context.user
            customer = account.customer
            StripeCustomer.modify(
                customer.id,
                name=input.name,
                email=input.email,
                address={
                    "city": input.address.city,
                    "line1": input.address.line,
                    "state": input.address.state,
                    "country": input.address.country,
                    "postal_code": input.address.postal_code,
                },
            )
            return cls(customer=customer)
        except Exception as e:
            logger.error(e)
            return cls(errors=[str(e)])


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
            admin = info.context.user

            for s in [
                *admin.subscription_set.all(),
                *admin.internal_subscription.all(),
            ]:
                if s.is_active:
                    return cls(errors=["Conta possui inscrição ativa"])

            price = DJStripePrice.objects.get(djstripe_id=price_id)
            subscription: DJStripeSubscription = admin.customer.subscribe(
                price=price.id,
                payment_behavior="default_incomplete",
                payment_settings={"save_default_payment_method": "on_subscription"},
            )
            Subscription.objects.create(admin=admin, subscription=subscription)
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
            subscription = Subscription.objects.get(id=subscription_id)
            subscription = subscription.subscription
            subscription = subscription.cancel()
            return None
        except Exception as e:
            logger.error(e)
            return cls(errors=[str(e)])


class StripeSubscriptionCustomerCreateMutation(Mutation):
    """Add account to subscription"""

    ok = Boolean()
    errors = List(String)

    class Arguments:
        account_id = ID(required=True)
        subscription_id = ID(required=True)

    @classmethod
    @login_required
    def mutate(cls, root, info, account_id, subscription_id):
        try:
            admin = info.context.user
            account = Account.objects.get(id=account_id)

            for s in [
                *account.subscription_set.all(),
                *account.internal_subscription.all(),
            ]:
                if s.is_active:
                    return cls(errors=["Conta possui inscrição ativa"])

            subscription = Subscription.objects.get(id=subscription_id)
            assert admin.id == subscription.admin.id
            add_user(account.email)
            subscription.subscribers.add(account)
            return cls(ok=True)
        except Exception as e:
            logger.error(e)
            return cls(errors=[str(e)])


class StripeSubscriptionCustomerDeleteMutation(Mutation):
    """Remove account from subscription"""

    ok = Boolean()
    errors = List(String)

    class Arguments:
        account_id = ID(required=True)
        subscription_id = ID(required=True)

    @classmethod
    @login_required
    def mutate(cls, root, info, account_id, subscription_id):
        try:
            admin = info.context.user
            account = Account.objects.get(id=account_id)
            subscription = Subscription.objects.get(id=subscription_id)
            assert admin.id == subscription.admin.id
            remove_user(account.email)
            subscription.subscribers.remove(account)
            return cls(ok=True)
        except Exception as e:
            logger.error(e)
            return cls(errors=[str(e)])


class Query(ObjectType):
    stripe_price = PlainTextNode.Field(StripePriceNode)
    all_stripe_price = DjangoFilterConnectionField(StripePriceNode)


class Mutation(ObjectType):
    create_stripe_customer = StripeCustomerCreateMutation.Field()
    update_stripe_customer = StripeCustomerUpdateMutation.Field()
    create_stripe_subscription = StripeSubscriptionCreateMutation.Field()
    delete_stripe_subscription = StripeSubscriptionDeleteMutation.Field()
    create_stripe_customer_subscription = StripeSubscriptionCustomerCreateMutation.Field()
    update_stripe_customer_subscription = StripeSubscriptionCustomerDeleteMutation.Field()


# Reference
# https://stripe.com/docs/billing/subscriptions/build-subscriptions?ui=elementsf
