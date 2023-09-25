# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest
from django.test.client import Client
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from basedosdados_api.account.models import Account


@pytest.mark.django_db
@patch("basedosdados_api.account.signals.is_prod", new=lambda: True)
def test_account_create():
    account = Account.objects.create(
        username="john.doe",
        email="john.doe@email.com",
    )
    assert account.is_active is False


@pytest.mark.django_db
@patch("basedosdados_api.account.signals.EmailMultiAlternatives")
@patch("basedosdados_api.account.signals.is_prod", new=lambda: True)
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
@patch("basedosdados_api.account.signals.is_prod", new=lambda: True)
def test_activate_account_confirmation(mock: MagicMock, client: Client):
    account = Account.objects.create(
        username="john.doe",
        email="john.doe@email.com",
    )
    uid = mock.call_args[0][1]["uid"]
    token = mock.call_args[0][1]["token"]
    #
    url = reverse("activate", args=[uid, token])
    response = client.post(url)
    assert response.status_code == 200
    assert response.json() == {}
    #
    account.refresh_from_db()
    assert account.is_active


@pytest.mark.django_db
@patch("basedosdados_api.account.views.EmailMultiAlternatives")
@patch("basedosdados_api.account.signals.is_prod", new=lambda: True)
def test_password_reset_request(mock: MagicMock, client: Client):
    account = Account.objects.create(
        username="john.doe",
        email="john.doe@email.com",
    )
    uid = urlsafe_base64_encode(force_bytes(account.pk))
    #
    url = reverse("password_reset", args=[uid])
    response = client.post(url)
    assert response.status_code == 200
    assert response.json() == {}
    #
    assert mock.call_args[0][0] == "Base dos Dados: Redefinição de Senha"
    assert mock.call_args[0][3] == ["john.doe@email.com"]
    assert "reset_password" in mock.mock_calls[1][1][0]


@pytest.mark.django_db
@patch("basedosdados_api.account.views.render_to_string")
@patch("basedosdados_api.account.signals.render_to_string")
@patch("basedosdados_api.account.signals.is_prod", new=lambda: True)
def test_password_reset_confirmation(mock_signal: MagicMock, mock_view: MagicMock, client: Client):
    # Create account
    account = Account.objects.create(
        username="john.doe",
        email="john.doe@email.com",
    )
    password0 = account.password
    uid = mock_signal.call_args[0][1]["uid"]
    token = mock_signal.call_args[0][1]["token"]
    # Request password reset
    url = reverse("password_reset", args=[uid])
    response = client.post(url)
    uid = mock_view.call_args[0][1]["uid"]
    token = mock_view.call_args[0][1]["token"]
    # Execute password reset
    url = reverse("password_reset_confirm", args=[uid, token])
    response = client.post(url, data={"password": "12345678"}, content_type="application/json")
    assert response.status_code == 200
    assert response.json() == {}
    # Verify password reset
    account.refresh_from_db()
    password1 = account.password
    assert password0 != password1
