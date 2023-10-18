# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest

from bd_api.apps.account.models import Account


@pytest.mark.django_db
@patch("bd_api.apps.payment.signals.DJStripeCustomer")
@patch("bd_api.apps.payment.signals.is_prod", new=lambda: True)
def test_create_stripe_customer_signal(mock: MagicMock):
    Account.objects.create(
        username="john.doe",
        email="john.doe@email.com",
    )
    assert mock.create.called
