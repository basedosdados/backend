# -*- coding: utf-8 -*-
"""Tests for the account HTTP views.

These are the account activation, password reset and Google OAuth endpoints.
Two things here are security boundaries rather than ordinary behaviour: the
OAuth `state` check that stops CSRF, and _safe_frontend_origin, which keeps the
post-login redirect on an allowlist because that redirect carries a JWT in its
query string. Both are asserted explicitly below.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.core import mail
from django.test.client import Client
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from backend.apps.account.models import Account
from backend.apps.account.token import token_generator
from backend.apps.account.views import GoogleCallbackView, _safe_frontend_origin


@pytest.fixture(name="account")
def fixture_account():
    return Account.objects.create_user(
        email="john.doe@email.com",
        password="12345678",
        username="john.doe",
        first_name="John",
        last_name="Doe",
    )


def uid_of(account):
    return urlsafe_base64_encode(force_bytes(account.pk))


# ---------------------------------------------------------------------------
# Account activation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_activation_email_is_sent_for_a_known_uid(client: Client, account):
    response = client.post(reverse("activate", args=[uid_of(account)]))
    assert response.status_code == 200
    assert response.json() == {}
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["john.doe@email.com"]
    assert mail.outbox[0].subject == "Bem Vindo à Base dos Dados!"


@pytest.mark.django_db
def test_activation_rejects_a_malformed_uid(client: Client):
    response = client.post(reverse("activate", args=["not-a-uid"]))
    assert response.status_code == 422
    assert mail.outbox == []


@pytest.mark.django_db
def test_activation_rejects_an_unknown_account(client: Client):
    unknown = urlsafe_base64_encode(force_bytes("00000000-0000-0000-0000-000000000000"))
    response = client.post(reverse("activate", args=[unknown]))
    assert response.status_code == 422


@pytest.mark.django_db
def test_a_valid_token_activates_the_account(client: Client, account):
    assert account.is_active is False
    url = reverse("activate", args=[uid_of(account), token_generator.make_token(account)])
    response = client.post(url)
    assert response.status_code == 200
    account.refresh_from_db()
    assert account.is_active is True


@pytest.mark.django_db
def test_an_invalid_token_does_not_activate_the_account(client: Client, account):
    url = reverse("activate", args=[uid_of(account), "wrong-token"])
    response = client.post(url)
    assert response.status_code == 422
    account.refresh_from_db()
    assert account.is_active is False


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_password_reset_emails_a_known_account(client: Client, account):
    response = client.post(reverse("password_reset", args=[uid_of(account)]))
    assert response.status_code == 200
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "Base dos Dados: Redefinição de Senha"
    assert mail.outbox[0].to == ["john.doe@email.com"]


@pytest.mark.django_db
def test_password_reset_rejects_an_unknown_uid(client: Client):
    response = client.post(reverse("password_reset", args=["not-a-uid"]))
    assert response.status_code == 422
    assert mail.outbox == []


@pytest.mark.django_db
def test_a_valid_token_changes_the_password(client: Client, account):
    url = reverse(
        "password_reset_confirm", args=[uid_of(account), token_generator.make_token(account)]
    )
    response = client.post(url, data={"password": "new-password"}, content_type="application/json")
    assert response.status_code == 200
    account.refresh_from_db()
    assert account.check_password("new-password")
    assert not account.check_password("12345678")


@pytest.mark.django_db
def test_an_invalid_token_leaves_the_password_alone(client: Client, account):
    url = reverse("password_reset_confirm", args=[uid_of(account), "wrong-token"])
    response = client.post(url, data={"password": "new-password"}, content_type="application/json")
    assert response.status_code == 422
    account.refresh_from_db()
    assert account.check_password("12345678")


@pytest.mark.django_db
def test_a_token_does_not_work_twice(client: Client, account):
    """Changing the password invalidates the token that authorised the change."""
    token = token_generator.make_token(account)
    url = reverse("password_reset_confirm", args=[uid_of(account), token])
    assert (
        client.post(
            url, data={"password": "first-password"}, content_type="application/json"
        ).status_code
        == 200
    )
    assert (
        client.post(
            url, data={"password": "second-password"}, content_type="application/json"
        ).status_code
        == 422
    )
    account.refresh_from_db()
    assert account.check_password("first-password")


# ---------------------------------------------------------------------------
# The redirect allowlist
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_safe_frontend_origin_accepts_an_allowlisted_origin():
    """Outside a remote environment the allowlist is the local frontend."""
    assert _safe_frontend_origin("http://localhost:3000") == "http://localhost:3000"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "candidate",
    [
        "https://evil.example.com",
        "http://localhost:3000.evil.com",
        "https://basedosdados.org",  # a production origin, not allowed locally
        "",
        None,
    ],
)
def test_safe_frontend_origin_rejects_everything_else(candidate):
    assert _safe_frontend_origin(candidate) is None


# ---------------------------------------------------------------------------
# Google OAuth: starting the flow
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_google_login_redirects_to_google_and_stores_state(client: Client):
    response = client.get(reverse("google_auth"))
    assert response.status_code == 302
    assert response.url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    state = client.session["oauth_state"]
    assert state and f"state={state}" in response.url


@pytest.mark.django_db
def test_google_login_remembers_an_allowlisted_origin(client: Client):
    client.get(reverse("google_auth"), {"redirect_origin": "http://localhost:3000"})
    assert client.session["frontend_origin"] == "http://localhost:3000"


@pytest.mark.django_db
def test_google_login_discards_an_unlisted_origin(client: Client):
    client.get(reverse("google_auth"), {"redirect_origin": "https://evil.example.com"})
    assert "frontend_origin" not in client.session


# ---------------------------------------------------------------------------
# Google OAuth: the callback
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_callback_reports_an_error_from_google(client: Client):
    response = client.get(reverse("google_callback"), {"error": "access_denied"})
    assert response.status_code == 400
    assert "access_denied" in response.json()["error"]


@pytest.mark.django_db
def test_callback_requires_an_authorization_code(client: Client):
    response = client.get(reverse("google_callback"), {"state": "whatever"})
    assert response.status_code == 400


@pytest.mark.django_db
def test_callback_rejects_a_mismatched_state(client: Client):
    """The state check is what stops a cross-site request forging a login."""
    client.get(reverse("google_auth"))
    response = client.get(reverse("google_callback"), {"code": "abc", "state": "attacker"})
    assert response.status_code == 400
    assert response.json()["error"] == "Estado inválido"


@pytest.mark.django_db
def test_callback_rejects_a_missing_state(client: Client):
    client.get(reverse("google_auth"))
    response = client.get(reverse("google_callback"), {"code": "abc"})
    assert response.status_code == 400


def start_flow(client, **params):
    """Run the login step so the session carries a valid state, and return it."""
    client.get(reverse("google_auth"), params)
    return client.session["oauth_state"]


@pytest.mark.django_db
@patch.object(GoogleCallbackView, "_get_user_info")
@patch.object(GoogleCallbackView, "_exchange_code_for_token")
def test_callback_creates_an_account_and_redirects_with_a_token(
    exchange: MagicMock, user_info: MagicMock, client: Client
):
    exchange.return_value = {"access_token": "at", "id_token": "it"}
    user_info.return_value = {"email": "jane@email.com", "id": "google-123", "name": "Jane Roe"}

    state = start_flow(client)
    response = client.get(reverse("google_callback"), {"code": "abc", "state": state})

    assert response.status_code == 302
    assert "login=success" in response.url
    assert "token=" in response.url

    account = Account.objects.get(email="jane@email.com")
    assert account.is_active is True
    assert account.google_sub == "google-123"
    assert account.first_name == "Jane"
    assert account.last_name == "Roe"


@pytest.mark.django_db
@patch.object(GoogleCallbackView, "_get_user_info")
@patch.object(GoogleCallbackView, "_exchange_code_for_token")
def test_callback_returns_to_the_origin_the_login_started_on(
    exchange: MagicMock, user_info: MagicMock, client: Client
):
    exchange.return_value = {"access_token": "at"}
    user_info.return_value = {"email": "jane@email.com", "id": "google-123", "name": "Jane"}

    state = start_flow(client, redirect_origin="http://localhost:3000")
    response = client.get(reverse("google_callback"), {"code": "abc", "state": state})
    assert response.url.startswith("http://localhost:3000/user/login")


@pytest.mark.django_db
@patch.object(GoogleCallbackView, "_exchange_code_for_token", return_value=None)
def test_callback_redirects_with_an_error_when_the_exchange_fails(
    exchange: MagicMock, client: Client
):
    state = start_flow(client)
    response = client.get(reverse("google_callback"), {"code": "abc", "state": state})
    assert response.status_code == 302
    assert "error=auth_failed" in response.url


@pytest.mark.django_db
@patch.object(GoogleCallbackView, "_get_user_info", return_value=None)
@patch.object(GoogleCallbackView, "_exchange_code_for_token")
def test_callback_redirects_with_an_error_when_user_info_fails(
    exchange: MagicMock, user_info: MagicMock, client: Client
):
    exchange.return_value = {"access_token": "at"}
    state = start_flow(client)
    response = client.get(reverse("google_callback"), {"code": "abc", "state": state})
    assert "error=user_info_failed" in response.url


@pytest.mark.django_db
@patch.object(GoogleCallbackView, "_get_user_info")
@patch.object(GoogleCallbackView, "_exchange_code_for_token")
def test_callback_redirects_with_an_error_when_the_account_cannot_be_built(
    exchange: MagicMock, user_info: MagicMock, client: Client
):
    exchange.return_value = {"access_token": "at"}
    user_info.return_value = {"name": "No Email"}  # missing email and id
    state = start_flow(client)
    response = client.get(reverse("google_callback"), {"code": "abc", "state": state})
    assert "error=account_creation_failed" in response.url


# ---------------------------------------------------------------------------
# Account creation from Google profile data
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_google_account_creation_derives_a_username_from_the_email():
    account = GoogleCallbackView()._create_or_update_account(
        {"email": "jane.roe@email.com", "id": "google-123", "name": "Jane Roe"}
    )
    assert account.username == "jane.roe"


@pytest.mark.django_db
def test_google_account_creation_disambiguates_a_taken_username(account):
    """account already holds the username "john.doe"."""
    created = GoogleCallbackView()._create_or_update_account(
        {"email": "john.doe@other.com", "id": "google-456", "name": "John Doe"}
    )
    assert created.username == "john.doe1"


@pytest.mark.django_db
def test_google_login_links_and_activates_an_existing_account(account):
    assert account.is_active is False
    linked = GoogleCallbackView()._create_or_update_account(
        {"email": "john.doe@email.com", "id": "google-789", "name": "John Doe"}
    )
    assert linked.pk == account.pk
    assert linked.google_sub == "google-789"
    account.refresh_from_db()
    assert account.is_active is True


@pytest.mark.django_db
def test_a_single_word_name_leaves_the_last_name_empty():
    account = GoogleCallbackView()._create_or_update_account(
        {"email": "cher@email.com", "id": "google-1", "name": "Cher"}
    )
    assert account.first_name == "Cher"
    assert account.last_name == ""


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_info",
    [
        {"id": "google-1", "name": "No Email"},
        {"email": "no.sub@email.com", "name": "No Sub"},
        {},
    ],
)
def test_google_account_creation_requires_an_email_and_a_google_id(user_info):
    assert GoogleCallbackView()._create_or_update_account(user_info) is None


@pytest.mark.django_db
def test_token_exchange_returns_none_on_a_request_error():
    with patch("backend.apps.account.views.requests.post") as post:
        post.side_effect = __import__("requests").RequestException("boom")
        assert GoogleCallbackView()._exchange_code_for_token("abc") is None


@pytest.mark.django_db
def test_user_info_returns_none_on_a_request_error():
    with patch("backend.apps.account.views.requests.get") as get:
        get.side_effect = __import__("requests").RequestException("boom")
        assert GoogleCallbackView()._get_user_info("at") is None


@pytest.mark.django_db
def test_token_exchange_returns_the_payload():
    with patch("backend.apps.account.views.requests.post") as post:
        post.return_value.json.return_value = {"access_token": "at"}
        post.return_value.raise_for_status.return_value = None
        assert GoogleCallbackView()._exchange_code_for_token("abc") == {"access_token": "at"}


@pytest.mark.django_db
def test_user_info_returns_the_payload():
    with patch("backend.apps.account.views.requests.get") as get:
        get.return_value.json.return_value = {"email": "jane@email.com"}
        get.return_value.raise_for_status.return_value = None
        assert GoogleCallbackView()._get_user_info("at") == {"email": "jane@email.com"}
