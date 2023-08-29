# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest
from django.test.client import Client
from django.urls import reverse

from basedosdados_api.account.models import Account


@pytest.mark.django_db
def test_account_create():
    account = Account.objects.create(
        username="john.doe",
        email="john.doe@email.com",
    )
    assert account.is_active is False


@pytest.mark.django_db
@patch("basedosdados_api.account.signals.EmailMultiAlternatives")
def test_activate_account_signal(mock: MagicMock):
    Account.objects.create(
        username="john.doe",
        email="john.doe@email.com",
    )
    assert mock.call_args[0][0] == "Bem Vindo à Base dos Dados!"
    assert mock.call_args[0][3] == ["john.doe@email.com"]
    assert "activate_account" in mock.mock_calls[1][1][0]


@pytest.mark.django_db
@patch("basedosdados_api.account.signals.render_to_string")
def test_activate_account_confirmation(mock: MagicMock, client: Client):
    account = Account.objects.create(
        username="john.doe",
        email="john.doe@email.com",
    )
    #
    uid = mock.call_args[0][1]["uid"]
    token = mock.call_args[0][1]["token"]
    url = reverse("activate", args=[uid, token])
    #
    response = client.post(url)
    assert response.status_code == 200
    assert response.json() == {}
    account.refresh_from_db()
    assert account.is_active


@pytest.mark.django_db
def test_password_reset_view(client):

    ...


@pytest.mark.django_db
def test_password_reset_confirm_view(client):
    ...
