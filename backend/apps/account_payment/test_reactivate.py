# -*- coding: utf-8 -*-
from unittest.mock import ANY, MagicMock, patch

import pytest
import stripe
from graphql import GraphQLResolveInfo

from backend.apps.account_payment.graphql import StripeReactivateSubscriptionMutation
from backend.apps.account_payment.reactivation import (
    COUPON_ERROR,
    GENERIC_ERROR,
    REACTIVATE_ACTION,
    promotion_code_rejection,
    reactivate_stripe_subscription,
)
from backend.apps.account_payment.webhooks import setup_intent_succeeded

GQL = "backend.apps.account_payment.graphql"
REACT = "backend.apps.account_payment.reactivation"
WH = "backend.apps.account_payment.webhooks"


def _stripe_sub(
    status="trialing",
    cancel_at=1_900_000_000,
    cancel_at_period_end=False,
    price_id="price_chatbot_month",
    product_id="prod_chatbot",
    default_payment_method=None,
    trial_end=1_800_000_000,
):
    return {
        "id": "sub_123",
        "trial_end": trial_end,
        "customer": "cus_123",
        "status": status,
        "cancel_at": cancel_at,
        "cancel_at_period_end": cancel_at_period_end,
        "default_payment_method": default_payment_method,
        "items": {"data": [{"id": "si_1", "price": {"id": price_id, "product": product_id}}]},
    }


def _promo(active=True, valid=True, customer=None, first_time_transaction=False):
    return stripe.PromotionCode.construct_from(
        {
            "id": "promo_1",
            "active": active,
            "customer": customer,
            "coupon": {"id": "coupon_1", "valid": valid},
            "restrictions": {"first_time_transaction": first_time_transaction},
        },
        "sk_test",
    )


def _info():
    info = MagicMock(spec=GraphQLResolveInfo)
    info.context = MagicMock()
    info.context.user.is_authenticated = True
    info.context.user.is_anonymous = False
    return info


def _internal(is_pro=False):
    internal = MagicMock()
    internal.subscription.id = "sub_123"
    internal.is_pro = is_pro
    return internal


@pytest.fixture
def gql():
    """Patch every external dependency of the mutation."""
    with (
        patch(f"{GQL}.Subscription") as subscription,
        patch(f"{GQL}.djstripe_subscription_is_chatbot", return_value=True) as is_chatbot,
        patch(f"{GQL}.retrieve_stripe_subscription") as retrieve,
        patch(f"{GQL}.StripeCustomer") as stripe_customer,
        patch(f"{GQL}.SetupIntent") as setup_intent,
        patch(f"{GQL}.get_stripe_promo") as get_promo,
        patch(f"{GQL}.DJStripePrice") as djstripe_price,
        patch(f"{GQL}.reactivate_stripe_subscription") as reactivate,
        patch(f"{GQL}.get_backend_url", return_value="http://backend"),
        patch(f"{REACT}.stripe.Charge") as charge,
    ):
        subscription.objects.filter.return_value.select_related.return_value.first.return_value = (
            _internal()
        )
        retrieve.return_value = _stripe_sub()
        stripe_customer.retrieve.return_value = {"invoice_settings": {}}
        setup_intent.create.return_value.client_secret = "seti_secret"
        get_promo.return_value = _promo()
        charge.list.return_value = {"data": []}
        yield MagicMock(
            subscription=subscription,
            is_chatbot=is_chatbot,
            retrieve=retrieve,
            stripe_customer=stripe_customer,
            setup_intent=setup_intent,
            get_promo=get_promo,
            djstripe_price=djstripe_price,
            reactivate=reactivate,
            charge=charge,
        )


def _mutate(**kwargs):
    return StripeReactivateSubscriptionMutation.mutate(
        None, _info(), subscription_id="uuid", **kwargs
    )


# --- mutation ---------------------------------------------------------------


def test_subscription_of_another_user_is_not_found(gql):
    gql.subscription.objects.filter.return_value.select_related.return_value.first.return_value = (
        None
    )
    result = _mutate()
    assert result.errors == ["Assinatura não encontrada."]
    gql.reactivate.assert_not_called()


def test_unknown_product_is_rejected(gql):
    gql.is_chatbot.return_value = False
    result = _mutate()
    assert result.errors == ["Este plano não pode ser reativado."]


def test_subscription_without_scheduled_cancellation_is_rejected(gql):
    gql.retrieve.return_value = _stripe_sub(cancel_at=None)
    result = _mutate()
    assert result.errors == ["Esta assinatura não possui cancelamento agendado."]


def test_ended_subscription_is_rejected(gql):
    gql.retrieve.return_value = _stripe_sub(status="canceled")
    result = _mutate()
    assert result.errors == ["Esta assinatura não possui cancelamento agendado."]


def test_invalid_coupon_is_rejected(gql):
    gql.get_promo.side_effect = Exception("not found")
    result = _mutate(coupon="NOPE")
    assert result.errors == ["Cupom inválido."]
    gql.setup_intent.create.assert_not_called()


def test_inactive_coupon_is_rejected(gql):
    gql.get_promo.return_value = _promo(active=False)
    result = _mutate(coupon="OLD")
    assert result.errors == ["Cupom inválido."]
    gql.setup_intent.create.assert_not_called()


def test_first_purchase_coupon_is_rejected_for_paying_customer(gql):
    gql.get_promo.return_value = _promo(first_time_transaction=True)
    gql.charge.list.return_value = {"data": [{"status": "succeeded"}]}

    result = _mutate(coupon="FIRST")

    assert result.errors == ["Este cupom vale apenas para a primeira compra."]
    gql.setup_intent.create.assert_not_called()


def test_trial_without_card_returns_setup_intent(gql):
    result = _mutate(coupon="SAVE20")

    assert result.client_secret == "seti_secret"
    assert result.errors is None
    # Nothing changes on the subscription until the card is confirmed.
    gql.reactivate.assert_not_called()
    kwargs = gql.setup_intent.create.call_args.kwargs
    assert kwargs["customer"] == "cus_123"
    assert kwargs["usage"] == "off_session"
    assert kwargs["metadata"] == {
        "action": REACTIVATE_ACTION,
        "subscription_id": "sub_123",
        "backend_url": "http://backend",
        "promotion_code": "promo_1",
    }


def test_trial_always_asks_for_card_even_with_saved_card(gql):
    gql.retrieve.return_value = _stripe_sub(default_payment_method="pm_saved")
    gql.stripe_customer.retrieve.return_value = {
        "invoice_settings": {"default_payment_method": "pm_saved"}
    }

    result = _mutate()

    assert result.client_secret == "seti_secret"
    assert result.ok is None
    gql.setup_intent.create.assert_called_once()
    gql.reactivate.assert_not_called()


def test_paid_subscriber_without_card_asks_for_card(gql):
    gql.retrieve.return_value = _stripe_sub(
        status="active", cancel_at=None, cancel_at_period_end=True
    )

    result = _mutate()

    assert result.client_secret == "seti_secret"


def test_trial_can_switch_interval(gql):
    price = MagicMock(id="price_chatbot_year")
    price.product.id = "prod_chatbot"
    gql.djstripe_price.objects.filter.return_value.first.return_value = price

    result = _mutate(price_id="42")

    assert result.client_secret == "seti_secret"
    metadata = gql.setup_intent.create.call_args.kwargs["metadata"]
    assert metadata["price_id"] == "price_chatbot_year"


def test_unknown_price_is_rejected(gql):
    gql.djstripe_price.objects.filter.return_value.first.return_value = None

    result = _mutate(price_id="42")

    assert result.errors == ["Este preço não está mais disponível."]


def test_inactive_price_is_rejected(gql):
    gql.djstripe_price.objects.filter.return_value.first.return_value = MagicMock(active=False)

    result = _mutate(price_id="42")

    assert result.errors == ["Este preço não está mais disponível."]


def test_same_price_is_not_a_switch(gql):
    price = MagicMock(id="price_chatbot_month")
    gql.djstripe_price.objects.filter.return_value.first.return_value = price

    _mutate(price_id="42")

    assert "price_id" not in gql.setup_intent.create.call_args.kwargs["metadata"]


def test_paid_subscription_cannot_switch_interval(gql):
    gql.retrieve.return_value = _stripe_sub(
        status="active", cancel_at=None, cancel_at_period_end=True
    )
    price = MagicMock(id="price_chatbot_year")
    price.product.id = "prod_chatbot"
    gql.djstripe_price.objects.filter.return_value.first.return_value = price

    result = _mutate(price_id="42")

    assert result.errors == ["A troca de plano só é permitida durante o período de teste."]


def test_bdpro_cannot_switch_interval(gql):
    gql.is_chatbot.return_value = False
    gql.subscription.objects.filter.return_value.select_related.return_value.first.return_value = (
        _internal(is_pro=True)
    )
    price = MagicMock(id="price_bdpro_year")
    gql.djstripe_price.objects.filter.return_value.first.return_value = price

    result = _mutate(price_id="42")

    assert result.errors == ["A troca de plano só é permitida durante o período de teste."]


def test_price_from_another_product_is_rejected(gql):
    price = MagicMock(id="price_bdpro_month")
    price.product.id = "prod_bdpro"
    gql.djstripe_price.objects.filter.return_value.first.return_value = price

    result = _mutate(price_id="42")

    assert result.errors == ["Este preço não pertence ao mesmo produto."]


def test_paid_subscriber_with_card_is_reactivated_directly(gql):
    gql.is_chatbot.return_value = False
    gql.subscription.objects.filter.return_value.select_related.return_value.first.return_value = (
        _internal(is_pro=True)
    )
    gql.retrieve.return_value = _stripe_sub(
        status="active", cancel_at=None, cancel_at_period_end=True
    )
    gql.stripe_customer.retrieve.return_value = {
        "invoice_settings": {"default_payment_method": "pm_card"}
    }

    result = _mutate(coupon="SAVE20")

    assert result.ok is True
    assert result.client_secret is None
    gql.setup_intent.create.assert_not_called()
    gql.reactivate.assert_called_once_with(
        "sub_123",
        payment_method="pm_card",
        price_id=None,
        promotion_code="promo_1",
    )


def test_stripe_coupon_error_is_translated(gql):
    gql.retrieve.return_value = _stripe_sub(
        status="active", cancel_at=None, cancel_at_period_end=True, default_payment_method="pm_card"
    )
    gql.reactivate.side_effect = stripe.error.InvalidRequestError(
        "first time only", param="discounts"
    )

    result = _mutate(coupon="FIRST")

    assert result.errors == [COUPON_ERROR]


def test_other_errors_do_not_leak_details(gql):
    gql.retrieve.side_effect = stripe.error.APIConnectionError("connection reset")
    assert _mutate().errors == [GENERIC_ERROR]

    gql.retrieve.side_effect = KeyError("items")
    assert _mutate().errors == [GENERIC_ERROR]


# --- promotion_code_rejection -------------------------------------------------


@patch(f"{REACT}.stripe.Charge")
def test_promotion_code_rejection(charge):
    charge.list.return_value = {"data": [{"status": "failed"}]}

    assert promotion_code_rejection(None, "cus_123") == "Cupom inválido."
    assert promotion_code_rejection(_promo(valid=False), "cus_123") == (
        "Este cupom não está mais ativo."
    )
    assert promotion_code_rejection(_promo(customer="cus_other"), "cus_123") == (
        "Este cupom não está disponível para a sua conta."
    )
    assert promotion_code_rejection(_promo(customer="cus_123"), "cus_123") is None
    # Only failed charges: still a first purchase.
    assert promotion_code_rejection(_promo(first_time_transaction=True), "cus_123") is None


# --- reactivate_stripe_subscription -------------------------------------------


@patch(f"{REACT}.DJStripeSubscription")
@patch(f"{REACT}.stripe.Subscription")
def test_reactivate_clears_cancel_at_and_keeps_trial(stripe_subscription, djstripe_sub):
    stripe_subscription.retrieve.return_value = _stripe_sub()

    reactivate_stripe_subscription(
        "sub_123",
        payment_method="pm_card",
        price_id="price_chatbot_year",
        promotion_code="promo_1",
    )

    stripe_subscription.modify.assert_called_once_with(
        "sub_123",
        proration_behavior="none",
        stripe_version=ANY,
        cancel_at="",
        default_payment_method="pm_card",
        discounts=[{"promotion_code": "promo_1"}],
        items=[{"id": "si_1", "price": "price_chatbot_year"}],
        # Unchanged trial end, so the price switch can't end the trial early.
        trial_end=1_800_000_000,
    )
    djstripe_sub.sync_from_stripe_data.assert_called_once()


@patch(f"{REACT}.DJStripeSubscription")
@patch(f"{REACT}.stripe.Subscription")
def test_reactivate_without_price_switch_does_not_touch_trial(stripe_subscription, djstripe_sub):
    stripe_subscription.retrieve.return_value = _stripe_sub()

    reactivate_stripe_subscription("sub_123", payment_method="pm_card")

    assert "trial_end" not in stripe_subscription.modify.call_args.kwargs
    assert "items" not in stripe_subscription.modify.call_args.kwargs


@patch(f"{REACT}.DJStripeSubscription")
@patch(f"{REACT}.stripe.Subscription")
def test_reactivate_clears_cancel_at_period_end(stripe_subscription, djstripe_sub):
    stripe_subscription.retrieve.return_value = _stripe_sub(
        status="active", cancel_at=1_900_000_000, cancel_at_period_end=True
    )

    reactivate_stripe_subscription("sub_123")

    stripe_subscription.modify.assert_called_once_with(
        "sub_123", proration_behavior="none", stripe_version=ANY, cancel_at_period_end=False
    )


@patch(f"{REACT}.DJStripeSubscription")
@patch(f"{REACT}.stripe.Subscription")
def test_reactivate_is_noop_when_not_reactivatable(stripe_subscription, djstripe_sub):
    stripe_subscription.retrieve.return_value = _stripe_sub(cancel_at=None)

    assert reactivate_stripe_subscription("sub_123") is None
    stripe_subscription.modify.assert_not_called()


# --- setup_intent.succeeded webhook -----------------------------------------


def _setup_intent_event(metadata):
    event = MagicMock()
    event.type = "setup_intent.succeeded"
    event.id = "evt_1"
    event.customer.id = "cus_123"
    event.customer.email = "user@email.com"
    event.data = {"object": {"payment_method": "pm_new", "metadata": metadata}}
    return event


@patch(f"{WH}.get_backend_url", return_value="http://backend")
@patch(f"{WH}.StripeCustomer")
@patch("backend.apps.account_payment.reactivation.reactivate_stripe_subscription")
def test_webhook_reactivates_instead_of_creating_subscription(
    reactivate, stripe_customer, _backend_url
):
    event = _setup_intent_event(
        {
            "action": REACTIVATE_ACTION,
            "subscription_id": "sub_123",
            "backend_url": "http://backend",
        }
    )

    setup_intent_succeeded(event)

    stripe_customer.modify.assert_called_once_with(
        "cus_123", invoice_settings={"default_payment_method": "pm_new"}
    )
    reactivate.assert_called_once_with(
        "sub_123", payment_method="pm_new", price_id=None, promotion_code=None
    )
    event.customer.subscribe.assert_not_called()


@patch(f"{WH}.get_backend_url", return_value="http://backend")
@patch(f"{WH}.StripeCustomer")
@patch("backend.apps.account_payment.reactivation.reactivate_stripe_subscription")
def test_webhook_applies_price_and_coupon_from_metadata(reactivate, stripe_customer, _backend_url):
    event = _setup_intent_event(
        {
            "action": REACTIVATE_ACTION,
            "subscription_id": "sub_123",
            "backend_url": "http://backend",
            "price_id": "price_chatbot_year",
            "promotion_code": "promo_1",
        }
    )

    setup_intent_succeeded(event)

    reactivate.assert_called_once_with(
        "sub_123",
        payment_method="pm_new",
        price_id="price_chatbot_year",
        promotion_code="promo_1",
    )
    event.customer.subscribe.assert_not_called()


@patch(f"{WH}.get_backend_url", return_value="http://backend")
@patch(f"{WH}.StripeCustomer")
@patch("backend.apps.account_payment.reactivation.reactivate_stripe_subscription")
def test_webhook_does_not_raise_when_stripe_refuses(reactivate, stripe_customer, _backend_url):
    reactivate.side_effect = stripe.error.InvalidRequestError("refused", param="discounts")
    event = _setup_intent_event(
        {
            "action": REACTIVATE_ACTION,
            "subscription_id": "sub_123",
            "backend_url": "http://backend",
            "promotion_code": "promo_1",
        }
    )

    setup_intent_succeeded(event)

    event.customer.subscribe.assert_not_called()


@patch(f"{WH}.get_backend_url", return_value="http://backend")
@patch(f"{WH}.StripeCustomer")
@patch("backend.apps.account_payment.reactivation.reactivate_stripe_subscription")
def test_webhook_ignores_other_environments(reactivate, stripe_customer, _backend_url):
    event = _setup_intent_event(
        {
            "action": REACTIVATE_ACTION,
            "subscription_id": "sub_123",
            "backend_url": "http://other",
        }
    )

    setup_intent_succeeded(event)

    reactivate.assert_not_called()
