# -*- coding: utf-8 -*-
import stripe
from django.conf import settings
from djstripe.models import Customer as DJStripeCustomer
from djstripe.models import Price as DJStripePrice
from djstripe.models import Subscription as DJStripeSubscription
from graphene import (
    ID,
    Boolean,
    Field,
    Float,
    InputObjectType,
    Int,
    List,
    Mutation,
    ObjectType,
    String,
)
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql_jwt.decorators import login_required
from loguru import logger
from stripe import Customer as StripeCustomer
from stripe import SetupIntent

from backend.apps.account.models import Account, Subscription
from backend.apps.account_payment.webhooks import add_user, remove_user
from backend.custom.graphql_base import CountableConnection, PlainTextNode

if settings.STRIPE_LIVE_MODE:
    stripe.api_key = settings.STRIPE_LIVE_SECRET_KEY
else:
    stripe.api_key = settings.STRIPE_TEST_SECRET_KEY


class StripePriceNode(DjangoObjectType):
    _id = ID(name="_id")
    amount = Float()
    interval = String()
    trial_period_days = String()
    product_name = String()
    product_slug = String()
    product_slots = String()
    is_active = Boolean()

    class Meta:
        model = DJStripePrice
        fields = ("id",)
        filter_fields = {
            "id": ["exact"],
            "active": ["exact"],
        }
        interfaces = (PlainTextNode,)
        connection_class = CountableConnection

    def resolve__id(root, info):
        return root.djstripe_id

    def resolve_amount(root, info):
        if root.unit_amount:
            return root.unit_amount / 100
        return 0

    def resolve_interval(root, info):
        if recurring := root.recurring:
            return recurring.get("interval", "")

    def resolve_trial_period_days(root, info):
        if recurring := root.recurring:
            return recurring.get("trial_period_days", "")

    def resolve_product_name(root, info):
        return root.product.name

    def resolve_product_slug(root, info):
        return root.product.metadata.get("code", "")

    def resolve_product_slots(root, info):
        return root.product.metadata.get("slots", "0")

    def resolve_is_active(root, info):
        return root.active


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

    client_secret = String()
    errors = List(String)

    class Arguments:
        price_id = ID(required=True)
        coupon = String(required=False)

    @classmethod
    @login_required
    def mutate(cls, root, info, price_id, coupon=None):
        try:
            admin = info.context.user
            internal_subscriptions = admin.internal_subscription.all()

            for s in [
                *admin.subscription_set.all(),
                *internal_subscriptions,
            ]:
                if s.is_active:
                    return cls(errors=["Conta possui inscrição ativa"])

            price = DJStripePrice.objects.get(djstripe_id=price_id)
            is_trial_active = len(internal_subscriptions) == 0
            promotion_code = None

            try:
                promotion = get_stripe_promo(coupon)
                if promotion and promotion.active:
                    promotion_code = promotion.id
            except Exception:
                ...

            customer, _ = DJStripeCustomer.get_or_create(admin)
            price_id = price.id

            if promotion_code:
                discounts = [{"promotion_code": promotion_code}]
            else:
                discounts = []

            if is_trial_active:
                subscription = None
                setup_intent = SetupIntent.create(
                    customer=customer.id,
                    usage="off_session",
                    metadata={
                        "price_id": price_id,
                        "promotion_code": promotion_code,
                    },
                )
            else:
                subscription: DJStripeSubscription = customer.subscribe(
                    price=price_id,
                    payment_behavior="default_incomplete",
                    payment_settings={"save_default_payment_method": "on_subscription"},
                    discounts=discounts,
                )

            if subscription:
                payment_intent = subscription.latest_invoice.payment_intent
                return cls(client_secret=payment_intent.client_secret)

            return cls(client_secret=setup_intent.client_secret)
        except Exception as e:
            logger.error(e)
            return cls(errors=[str(e)])


class StripeCouponValidationMutation(Mutation):
    """Validate a Stripe coupon and return discount details"""

    is_valid = Boolean()
    discount_amount = Float()
    duration = String()
    duration_in_months = Int()
    errors = List(String)

    class Arguments:
        coupon = String(required=True)
        price_id = ID(required=True)

    @classmethod
    @login_required
    def mutate(cls, root, info, coupon, price_id):
        try:
            try:
                promotion_code_object = get_stripe_promo(coupon)
                if promotion_code_object and promotion_code_object.active:
                    coupon_object = stripe.Coupon.retrieve(promotion_code_object.coupon.id)
                else:
                    return cls(
                        is_valid=False,
                        discount_amount=0,
                        duration_in_months=0,
                        errors=["Cupom inválido"],
                    )
            except Exception as e:
                return cls(
                    is_valid=False,
                    discount_amount=0,
                    duration_in_months=0,
                    errors=["Cupom inválido", str(e)],
                )

            if not coupon_object.valid:
                return cls(
                    is_valid=False,
                    discount_amount=0,
                    duration_in_months=0,
                    errors=["Cupom não está ativo"],
                )

            price = DJStripePrice.objects.get(djstripe_id=price_id)
            price_amount = price.unit_amount / 100.0

            discount_amount = 0.0

            if coupon_object.amount_off:
                discount_amount = coupon_object.amount_off / 100.0
            elif coupon_object.percent_off:
                discount_amount = (coupon_object.percent_off / 100.0) * price_amount

            duration_in_months = coupon_object.duration_in_months
            duration = coupon_object.duration

            if coupon_object.duration != "repeating":
                duration_in_months = 0

            return cls(
                is_valid=True,
                discount_amount=discount_amount,
                duration_in_months=duration_in_months,
                duration=duration,
            )
        except Exception as e:
            logger.error(e)
            return cls(is_valid=False, errors=[str(e)])


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
            stripe_subscription = subscription.subscription
            stripe_subscription.cancel(at_period_end=True)
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


def get_stripe_promo(promotion_code):
    """
    Helper function to retrieve a Stripe Promotion Code by its code.

    :param promotion_code: The code of the promotion to be retrieved.
    :return: The Stripe Promotion Code object if found.
    :raises Exception: If the promotion code is not found or any error occurs.
    """
    if not promotion_code:
        raise Exception("Promotion code not provided")
    try:
        promotion_code_list = stripe.PromotionCode.list(code=promotion_code, limit=1)

        if promotion_code_list.data:
            return promotion_code_list.data[0]
        else:
            raise Exception("Promotion code not found")

    except Exception as e:
        raise Exception(f"Error retrieving promotion code: {str(e)}")


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
    validate_stripe_coupon = StripeCouponValidationMutation.Field()


# Reference
# https://stripe.com/docs/billing/subscriptions/build-subscriptions?ui=elementsf
