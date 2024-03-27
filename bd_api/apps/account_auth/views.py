# -*- coding: utf-8 -*-
from typing import Tuple, Union
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from requests import post

from bd_api.apps.account.models import Account
from bd_api.apps.account_auth.models import Access, Domain, Token


def get_redirect_uri(request: HttpRequest, default: str = None) -> str:
    # First from X-Original-Url header.
    redirect_uri = request.headers.get("X-Original-URL", None)
    if redirect_uri:
        return redirect_uri

    # Then from the query string.
    redirect_uri = request.GET.get("rd", None)
    if redirect_uri:
        return redirect_uri

    # Finally, from the default.
    return default


def is_authenticated(request: HttpRequest) -> Tuple[str, Token, Domain, Account, bool]:
    """
    This checks for authentication. It returns a tuple with 5 elements:
    - The redirect URI.
    - The token.
    - The domain.
    - The user.
    - Whether the authentication was successful.

    How it works:

    - First, it tries to extract the desired domain from the request.
    - If it fails, it returns a 401.

    - Then, if there's an user logged in, it iterates over its tokens,
        looking for a token with the desired domain.
    - If it finds one, it returns a 200.
    - If it doesn't, it returns a 401.

    - Finally, if no user is logged in, tries to extract the token from
        the request headers.
    - If it finds one, it checks if it's valid for the domain.
    - If it is, it returns a 200.
    - If it isn't, it returns a 401.

    - If no token is found, it returns a 401.
    """
    # Tries to extract the desired domain from the request.
    redirect_uri = get_redirect_uri(request)
    if not redirect_uri:
        # If it fails, it returns false.
        return redirect_uri, None, None, None, False

    # Tries to find the domain in the database.
    redirect_domain = urlparse(redirect_uri).netloc
    try:
        domain = Domain.objects.get(name=redirect_domain)
    except Domain.DoesNotExist:
        # If it fails, it returns false.
        return redirect_uri, None, None, None, False

    # If there's an user logged in, it iterates over its tokens
    if request.user.is_authenticated:
        for token in request.user.tokens.all():
            # If it finds one, it returns true.
            if token.domain == domain:
                return redirect_uri, token, domain, request.user, True
        # If it doesn't, it returns false.
        return redirect_uri, None, domain, request.user, False

    # Finally, if no user is logged in, tries to extract the token from
    # the request headers.
    token = request.headers.get("Authorization", None)
    if not token:
        # If it fails, it returns false.
        return redirect_uri, None, domain, None, False

    # If it finds the Authorization header, extract token
    try:
        token = token.split(" ")[1]
    except IndexError:
        # If it fails, it returns false.
        return redirect_uri, None, domain, None, False

    # If it finds one, it checks if it's valid for the domain.
    try:
        token: Token = Token.objects.get(token=token)
    except Token.DoesNotExist:
        # If it fails, it returns false.
        return redirect_uri, None, domain, None, False

    # Token must have same domain, its expiry date must be in the future,
    # and it must be active.
    if (token.domain == domain) and (token.expiry_date > timezone.now()) and (token.is_active):
        return redirect_uri, token, domain, token.user, True

    # If it isn't, it returns a 401.
    return redirect_uri, token, domain, token.user, False


def store_access(
    token: Union[str, Token], domain: Union[str, Domain], user: Account, success: bool
) -> None:
    try:
        if isinstance(token, str):
            token: Token = Token.objects.get(token=token)
    except Token.DoesNotExist:
        token = None
    try:
        if isinstance(domain, str):
            domain: Domain = Domain.objects.get(name=domain)
    except Domain.DoesNotExist:
        domain = None
    if user is None and token is not None:
        user = token.user
    access = Access(token=token, domain=domain, success=success, user=user)
    access.save()


def validate_recaptcha_token(token: str) -> bool:
    """
    Validates the recaptcha token.
    """
    url = "https://www.google.com/recaptcha/api/siteverify"
    data = {"secret": settings.RECAPTCHA_SECRET_KEY, "response": token}
    response = post(url, data=data)
    return response.json()["success"]


def auth(request: HttpRequest) -> HttpResponse:
    """
    This returns either 200 or 401. For either case, we store the
    access log in the database.

    How it works:

    - First, it tries to extract the desired domain from the request.
    - If it fails, it returns a 401.

    - Then, if there's an user logged in, it iterates over its tokens,
        looking for a token with the desired domain.
    - If it finds one, it returns a 200.
    - If it doesn't, it returns a 401.

    - Finally, if no user is logged in, tries to extract the token from
        the request headers.
    - If it finds one, it checks if it's valid for the domain.
    - If it is, it returns a 200.
    - If it isn't, it returns a 401.

    - If no token is found, it returns a 401.
    """
    _, token, domain, user, success = is_authenticated(request)
    if not success:
        store_access(token=token, domain=domain, user=user, success=success)
    if success:
        return HttpResponse(status=200)
    return HttpResponse(status=401)


def signin(request: HttpRequest) -> HttpResponse:
    redirect_uri, _, _, user, success = is_authenticated(request)
    if success:
        if redirect_uri:
            return redirect(redirect_uri)
        return HttpResponse("You are already signed in. <a href='/auth/logout/'>Sign out</a>.")
    if request.user and request.user.is_authenticated:
        if redirect_uri:
            return HttpResponse("You do not have access to this page.", status=401)
        return HttpResponse("You are already signed in. <a href='/auth/logout/'>Sign out</a>.")
    if request.method == "POST":
        username = request.POST.get("username", None)
        password = request.POST.get("password", None)
        recaptcha_response = request.POST.get("g-recaptcha-response", None)
        if (not recaptcha_response) or (not validate_recaptcha_token(recaptcha_response)):
            return HttpResponse(
                "Captcha is invalid. <a href='/auth/login/'>Try again</a>.", status=401
            )
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if redirect_uri:
                    return redirect(redirect_uri)
                return HttpResponse("You are now signed in. <a href='/auth/logout/'>Sign out</a>.")
        return HttpResponse("Invalid username or password.", status=401)
    return render(
        request,
        "signin.html",
        context={"recaptcha_site_key": settings.RECAPTCHA_SITE_KEY},
    )


def signout(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        logout(request)
        redirect_url = get_redirect_uri(request, default=None)
        if redirect_url:
            return redirect(redirect_url)
        return HttpResponse("You are now signed out. <a href='/auth/login/'>Sign in</a>.")
    return HttpResponse("You are not signed in. <a href='/auth/login/'>Sign in</a>.", status=401)
