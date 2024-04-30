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

URI = str
Status = bool


def auth(request: HttpRequest) -> HttpResponse:
    _, token, domain, user, success = authorize(request)
    if success:
        return HttpResponse(status=200)
    if not success:
        store_access(token=token, domain=domain, user=user, success=success)
    return HttpResponse(status=401)


def signin(request: HttpRequest) -> HttpResponse:
    redirect_uri, _, _, user, success = authorize(request)
    if success and redirect_uri:
        return redirect(redirect_uri)
    if success and not redirect_uri:
        return HttpResponse(
            "Please specify a redirect URL. <a href='/auth/logout/'>Sign out</a>.",
            status=422,
        )
    if request.user and request.user.is_authenticated and redirect_uri:
        return HttpResponse(
            "Please contact the support. <a href='/auth/logout/'>Sign out</a>.",
            status=403,
        )
    if request.user and request.user.is_authenticated and not redirect_uri:
        return HttpResponse(
            "Please contact the support. <a href='/auth/logout/'>Sign out</a>.",
            status=422,
        )
    if request.method == "GET":
        return render(
            request,
            "signin.html",
            context={"recaptcha_site_key": settings.RECAPTCHA_SITE_KEY},
        )
    if request.method == "POST":
        username = request.POST.get("username", None)
        password = request.POST.get("password", None)
        recaptcha_response = request.POST.get("g-recaptcha-response", None)
        if not recaptcha_response or not validate_recaptcha_token(recaptcha_response):
            return HttpResponse(
                "Invalid captcha. <a href='/auth/login/'>Try again</a>.",
                status=401,
            )
        if username and password:
            if user := authenticate(request, username=username, password=password):
                login(request, user)
                if redirect_uri:
                    return redirect(redirect_uri)
                return HttpResponse(
                    "Please specify a redirect URL. <a href='/auth/logout/'>Sign out</a>.",
                    status=422,
                )
        return HttpResponse(
            "Invalid username or password. <a href='/auth/login/'>Try again</a>.",
            status=401,
        )


def signout(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        logout(request)
    return redirect("login")


def authorize(request: HttpRequest) -> Tuple[URI, Token, Domain, Account, Status]:
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

    # If there's an user logged in
    if request.user.is_authenticated:
        # If user is staff, it returns true
        if request.user.is_staff:
            return redirect_uri, None, domain, request.user, True
        # If user is not staff, it iterates over its tokens
        for token in request.user.tokens.all():
            # If it finds one, it returns true.
            if token.domain == domain:
                return redirect_uri, token, domain, request.user, True
        # If it doesn't, it returns false.
        return redirect_uri, None, domain, request.user, False

    # Finally, if no user is logged in,
    # tries to extract the token from the request headers
    token = request.headers.get("Authorization", None)
    if not token:
        # If it fails, it returns false
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

    # Token must have same domain,
    # its expiry date must be in the future, and it must be active.
    if token.domain == domain and token.is_active:
        if not token.expiry_date or token.expiry_date > timezone.now():
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


def get_redirect_uri(request: HttpRequest, default: str = None) -> str:
    if redirect_uri := request.headers.get("X-Original-URL", None):
        return redirect_uri
    if redirect_uri := request.GET.get("rd", None):
        return redirect_uri
    return default


def validate_recaptcha_token(token: str) -> bool:
    url = "https://www.google.com/recaptcha/api/siteverify"
    data = {"secret": settings.RECAPTCHA_SECRET_KEY, "response": token}
    response = post(url, data=data)
    return response.json()["success"]
