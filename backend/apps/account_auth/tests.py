# -*- coding: utf-8 -*-
"""Tests for the account_auth gateway.

`/auth/` is an authorization endpoint: a reverse proxy calls it to decide whether
a request may reach a protected domain, so a 200 returned by mistake is an
authorization bypass. authorize() is the function that decides, and it has six
separate ways to say no. Each is covered here.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test.client import Client
from django.utils import timezone

from backend.apps.account.models import Account
from backend.apps.account_auth.models import Access, Domain, Token
from backend.apps.account_auth.views import get_redirect_uri, store_access

PROTECTED = "https://protected.basedosdados.org/dashboard"


@pytest.fixture(name="domain")
def fixture_domain():
    return Domain.objects.create(name="protected.basedosdados.org")


@pytest.fixture(name="user")
def fixture_user():
    account = Account.objects.create_user(
        email="john.doe@email.com",
        password="12345678",
        username="john.doe",
        first_name="John",
        last_name="Doe",
    )
    account.is_active = True
    account.save()
    return account


@pytest.fixture(name="token")
def fixture_token(user, domain):
    return Token.objects.create(user=user, domain=domain)


def auth(client, *, token=None, url=PROTECTED):
    headers = {"HTTP_X_ORIGINAL_URL": url} if url else {}
    if token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client.get("/auth/", **headers)


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_redirect_uri_is_refused(client: Client):
    assert auth(client, url=None).status_code == 401


@pytest.mark.django_db
def test_an_unregistered_domain_is_refused(client: Client, token):
    response = auth(client, token=token.token, url="https://not-registered.example.com/x")
    assert response.status_code == 401


@pytest.mark.django_db
def test_a_missing_authorization_header_is_refused(client: Client, domain):
    assert auth(client).status_code == 401


@pytest.mark.django_db
def test_a_malformed_authorization_header_is_refused(client: Client, domain):
    response = client.get("/auth/", HTTP_X_ORIGINAL_URL=PROTECTED, HTTP_AUTHORIZATION="Bearer")
    assert response.status_code == 401


@pytest.mark.django_db
def test_an_unknown_token_is_refused(client: Client, domain):
    assert auth(client, token="not-a-real-token").status_code == 401


@pytest.mark.django_db
def test_a_token_for_another_domain_is_refused(client: Client, user, domain):
    other = Domain.objects.create(name="other.basedosdados.org")
    other_token = Token.objects.create(user=user, domain=other)
    assert auth(client, token=other_token.token).status_code == 401


@pytest.mark.django_db
def test_an_inactive_token_is_refused(client: Client, token):
    token.is_active = False
    Token.objects.filter(pk=token.pk).update(is_active=False)
    assert auth(client, token=token.token).status_code == 401


@pytest.mark.django_db
def test_an_expired_token_is_refused(client: Client, token):
    Token.objects.filter(pk=token.pk).update(expiry_date=timezone.now() - timedelta(days=1))
    assert auth(client, token=token.token).status_code == 401


# ---------------------------------------------------------------------------
# Grants
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_valid_token_is_accepted(client: Client, token):
    assert auth(client, token=token.token).status_code == 200


@pytest.mark.django_db
def test_a_token_with_a_future_expiry_is_accepted(client: Client, token):
    Token.objects.filter(pk=token.pk).update(expiry_date=timezone.now() + timedelta(days=1))
    assert auth(client, token=token.token).status_code == 200


@pytest.mark.django_db
def test_a_token_with_no_expiry_never_expires(client: Client, token):
    assert token.expiry_date is None
    assert auth(client, token=token.token).status_code == 200


@pytest.mark.django_db
def test_a_logged_in_staff_user_is_accepted_without_a_token(client: Client, user, domain):
    user.is_admin = True
    user.save()
    client.force_login(user)
    assert auth(client).status_code == 200


@pytest.mark.django_db
def test_a_logged_in_user_with_a_matching_token_is_accepted(client: Client, user, token):
    client.force_login(user)
    assert auth(client).status_code == 200


@pytest.mark.django_db
def test_a_logged_in_user_without_a_token_for_the_domain_is_refused(client: Client, user, domain):
    client.force_login(user)
    assert auth(client).status_code == 401


# ---------------------------------------------------------------------------
# Failed attempts are recorded
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_refusal_is_recorded(client: Client, domain):
    auth(client)
    assert Access.objects.filter(success=False).count() == 1


@pytest.mark.django_db
def test_a_grant_is_not_recorded(client: Client, token):
    auth(client, token=token.token)
    assert Access.objects.count() == 0


@pytest.mark.django_db
def test_store_access_resolves_string_arguments(token, domain, user):
    store_access(token=token.token, domain=domain.name, user=None, success=True)
    access = Access.objects.get()
    assert access.token == token
    assert access.domain == domain
    assert access.user == user  # inferred from the token


@pytest.mark.django_db
def test_store_access_tolerates_unknown_names():
    store_access(token="nope", domain="nope", user=None, success=False)
    access = Access.objects.get()
    assert access.token is None
    assert access.domain is None


# ---------------------------------------------------------------------------
# Redirect URI resolution
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_the_original_url_header_wins(rf):
    request = rf.get("/auth/", {"rd": "https://from-query.example.com"})
    request.META["HTTP_X_ORIGINAL_URL"] = "https://from-header.example.com"
    assert get_redirect_uri(request) == "https://from-header.example.com"


@pytest.mark.django_db
def test_the_rd_query_parameter_is_the_fallback(rf):
    request = rf.get("/auth/", {"rd": "https://from-query.example.com"})
    assert get_redirect_uri(request) == "https://from-query.example.com"


@pytest.mark.django_db
def test_the_default_is_returned_when_neither_is_present(rf):
    assert get_redirect_uri(rf.get("/auth/"), default="fallback") == "fallback"
    assert get_redirect_uri(rf.get("/auth/")) is None


# ---------------------------------------------------------------------------
# Sign in and sign out
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_the_signin_page_renders(client: Client):
    response = client.get("/auth/login/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_signin_requires_a_captcha(client: Client):
    response = client.post(
        "/auth/login/", {"username": "john.doe@email.com", "password": "12345678"}
    )
    assert response.status_code == 401
    assert b"Invalid captcha" in response.content


@pytest.mark.django_db
@patch("backend.apps.account_auth.views.validate_recaptcha_token", return_value=True)
def test_signin_rejects_bad_credentials(captcha, client: Client, user):
    response = client.post(
        "/auth/login/",
        {
            "username": "john.doe@email.com",
            "password": "wrong-password",
            "g-recaptcha-response": "ok",
        },
    )
    assert response.status_code == 401
    assert b"Invalid username or password" in response.content


@pytest.mark.django_db
@patch("backend.apps.account_auth.views.validate_recaptcha_token", return_value=True)
def test_signin_without_a_redirect_asks_for_one(captcha, client: Client, user):
    response = client.post(
        "/auth/login/",
        {
            "username": "john.doe@email.com",
            "password": "12345678",
            "g-recaptcha-response": "ok",
        },
    )
    assert response.status_code == 422
    assert b"Please specify a redirect URL" in response.content


@pytest.mark.django_db
@patch("backend.apps.account_auth.views.validate_recaptcha_token", return_value=True)
def test_signin_redirects_on_success(captcha, client: Client, user, domain):
    response = client.post(
        f"/auth/login/?rd={PROTECTED}",
        {
            "username": "john.doe@email.com",
            "password": "12345678",
            "g-recaptcha-response": "ok",
        },
    )
    assert response.status_code == 302
    assert response.url == PROTECTED


@pytest.mark.django_db
def test_signout_redirects_to_login(client: Client, user):
    client.force_login(user)
    response = client.get("/auth/logout/")
    assert response.status_code == 302
    assert client.get("/auth/login/", follow=False).status_code == 200


@pytest.mark.django_db
def test_signout_is_safe_when_no_one_is_logged_in(client: Client):
    assert client.get("/auth/logout/").status_code == 302


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_token_value_is_generated_on_save(user, domain):
    token = Token.objects.create(user=user, domain=domain)
    assert token.token
    other = Token.objects.create(user=user, domain=domain)
    assert token.token != other.token


@pytest.mark.django_db
def test_saving_an_existing_token_rotates_its_value(user, domain):
    """Recorded, not endorsed: Token.save() regenerates unconditionally.

    Any later save rotates the token, so editing a Token in the admin, for
    instance to set an expiry date, silently invalidates the value the client
    is already using. Guarding the assignment with `if not self.token` would
    fix it, but that changes how an auth credential behaves and is left as a
    decision for the team rather than folded into a testing change.
    """
    token = Token.objects.create(user=user, domain=domain)
    original = token.token
    token.expiry_date = timezone.now() + timedelta(days=30)
    token.save()
    assert token.token != original


@pytest.mark.django_db
def test_model_string_representations(token, domain, user):
    assert str(domain) == "protected.basedosdados.org"
    assert str(token).startswith("john.doe - protected.basedosdados.org - ")
    access = Access.objects.create(token=token, domain=domain, user=user, success=True)
    assert " - OK - " in str(access)
    denied = Access.objects.create(success=False)
    assert " - ERR - NO_DOMAIN - NO_TOKEN" in str(denied)


@pytest.mark.django_db
def test_recaptcha_validation_reads_the_google_response():
    from backend.apps.account_auth.views import validate_recaptcha_token

    with patch("backend.apps.account_auth.views.post") as post:
        post.return_value.json.return_value = {"success": True}
        assert validate_recaptcha_token("t") is True
        post.return_value.json.return_value = {"success": False}
        assert validate_recaptcha_token("t") is False
