# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest

from backend.apps.account.models import Account
from backend.apps.account_payment.graphql import StripeSubscribeMutation


@pytest.fixture
def account():
    return Account.objects.create(
        is_active=True,
        username="coupon.campaign",
        password="12345678",
        email="coupon.campaign@email.com",
    )


def _mock_chatbot_price():
    price = MagicMock()
    price.product.metadata.get.return_value = "chatbot"
    price.id = "price_chatbot"
    return price


def _mock_info(account):
    info = MagicMock()
    info.context.user = account
    info.context.user.is_anonymous = False
    return info


@pytest.mark.django_db
@patch("backend.apps.account_payment.graphql.SetupIntent")
@patch("backend.apps.account_payment.graphql.DJStripeCustomer")
@patch("backend.apps.account_payment.graphql.DJStripePrice")
@patch("backend.apps.account_payment.graphql.get_stripe_promo")
@patch(
    "backend.apps.account_payment.graphql.account_eligible_for_chatbot_stripe_trial",
    return_value=True,
)
def test_skip_trial_creates_paid_subscription_with_coupon(
    _eligible,
    get_stripe_promo,
    djstripe_price,
    djstripe_customer,
    setup_intent,
    account,
):
    djstripe_price.objects.get.return_value = _mock_chatbot_price()

    promo = MagicMock()
    promo.active = True
    promo.id = "promo_save20"
    get_stripe_promo.return_value = promo

    customer = MagicMock()
    customer.id = "cus_123"
    subscription = MagicMock()
    subscription.latest_invoice.payment_intent.client_secret = "pi_secret"
    customer.subscribe.return_value = subscription
    djstripe_customer.get_or_create.return_value = (customer, True)

    result = StripeSubscribeMutation.mutate(
        None,
        _mock_info(account),
        price_id=1,
        coupon="SAVE20",
        skip_trial=True,
    )

    setup_intent.create.assert_not_called()
    customer.subscribe.assert_called_once()
    subscribe_kwargs = customer.subscribe.call_args.kwargs
    assert subscribe_kwargs["price"] == "price_chatbot"
    assert subscribe_kwargs["discounts"] == [{"promotion_code": "promo_save20"}]
    assert subscribe_kwargs["trial_end"] == "now"
    assert result.client_secret == "pi_secret"
    assert result.errors is None


@pytest.mark.django_db
@patch("backend.apps.account_payment.graphql.SetupIntent")
@patch("backend.apps.account_payment.graphql.DJStripeCustomer")
@patch("backend.apps.account_payment.graphql.DJStripePrice")
@patch(
    "backend.apps.account_payment.graphql.account_eligible_for_chatbot_stripe_trial",
    return_value=True,
)
def test_eligible_trial_without_skip_uses_setup_intent(
    _eligible,
    djstripe_price,
    djstripe_customer,
    setup_intent,
    account,
):
    djstripe_price.objects.get.return_value = _mock_chatbot_price()

    customer = MagicMock()
    customer.id = "cus_123"
    djstripe_customer.get_or_create.return_value = (customer, True)

    setup = MagicMock()
    setup.client_secret = "seti_secret"
    setup_intent.create.return_value = setup

    result = StripeSubscribeMutation.mutate(
        None,
        _mock_info(account),
        price_id=1,
        skip_trial=False,
    )

    customer.subscribe.assert_not_called()
    setup_intent.create.assert_called_once()
    assert result.client_secret == "seti_secret"
