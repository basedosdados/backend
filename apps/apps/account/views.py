# -*- coding: utf-8 -*-
from json import loads
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetView,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy as r
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView
from loguru import logger

from apps.apps.account.forms import RegisterForm
from apps.apps.account.token import token_generator
from apps.settings import EMAIL_HOST_USER


class LoadUserView:
    pass


class LoginView(SuccessMessageMixin, LoginView):
    template_name = "account/login.html"
    success_message = "Você está logado como %(username)s."
    success_url = r("home")


class LogoutView(SuccessMessageMixin, LogoutView):
    success_message = "Você saiu com sucesso."
    success_url = r("home")


class PasswordChangeView(SuccessMessageMixin, PasswordChangeView):
    template_name = "account/password_change.html"
    success_message = "Sua senha foi alterada com sucesso."
    success_url = r("home")


class PasswordResetView(SuccessMessageMixin, PasswordResetView):
    template_name = "account/password_reset.html"
    success_message = (
        "Enviamos um email com as instruções para você configurar uma nova senha, "
        "caso exista uma conta com o email fornecido. Você deve recebê-lo em breve."
        " Se você não receber o email, "
        "verifique se você digitou o endereço correto e verifique sua caixa de spam."
    )
    success_url = r("home")

    @method_decorator(csrf_exempt, name="dispatch")
    def dispatch(self, request, uidb64):
        """Generate token and send password reset email"""
        user_model = get_user_model()
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = user_model.objects.get(id=uid)
        except (TypeError, ValueError, OverflowError, user_model.DoesNotExist) as e:
            logger.error(e)
            user = None

        if user:
            to_email = user.email
            from_email = EMAIL_HOST_USER
            subject = "Base dos Dados: Redefinição de Senha"

            token = token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            content = render_to_string(
                "account/password_reset_email_v1.html",
                {
                    "name": user.full_name,
                    "domain": "basedosdados.org",
                    "uid": uid,
                    "token": token,
                },
            )

            msg = EmailMultiAlternatives(subject, "", from_email, [to_email])
            msg.attach_alternative(content, "text/html")
            msg.send()

            return JsonResponse({}, status=200)
        else:
            return JsonResponse({}, status=422)


class PasswordResetConfirmView(SuccessMessageMixin, PasswordResetConfirmView):
    template_name = "account/password_reset_confirm.html"
    success_message = "Sua senha foi alterada com sucesso."
    success_url = r("home")

    @method_decorator(csrf_exempt, name="dispatch")
    def dispatch(self, request, uidb64, token):
        """Verify token and reset password"""
        user_model = get_user_model()

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = user_model.objects.get(id=uid)
        except (TypeError, ValueError, OverflowError, user_model.DoesNotExist) as e:
            logger.error(e)
            user = None

        if user and token_generator.check_token(user, token):
            body = loads(request.body)
            user.set_password(body["password"])
            user.save()
            return JsonResponse({}, status=200)
        else:
            return JsonResponse({}, status=422)


class PasswordResetCompleteView(SuccessMessageMixin, PasswordResetCompleteView):
    template_name = "account/password_reset_complete.html"
    success_message = "Sua senha foi alterada com sucesso."
    success_url = r("home")


class RegisterView(SuccessMessageMixin, CreateView):
    form_class = RegisterForm
    model = get_user_model()
    template_name = "account/register.html"
    success_message = "Sua conta foi criada com sucesso."
    success_url = r("home")

    def form_valid(self, form):
        response = super().form_valid(form)
        form.cleaned_data.get("username")
        form.cleaned_data.get("password1")
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        subject = "Bem vindo(a) à Base dos Dados! Ative sua conta."
        message = render_to_string(
            "account/activation_email.html",
            {
                "user": user,
                "domain": get_current_site(self.request).domain,
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": token_generator.make_token(user),
            },
        )
        user.email_user(subject, message, settings.DEFAULT_FROM_EMAIL)

        messages.add_message(
            self.request,
            messages.SUCCESS,
            "Sua conta foi criada com sucesso. Enviamos um email com as instruções para você ativar sua conta, "
            "caso exista uma conta com o email fornecido. Você deve recebê-lo em breve. "
            "Se você não receber o email, verifique se você digitou o endereço correto e verifique sua caixa de spam.",
        )
        return response


class ActivateAccountView(View):
    @method_decorator(csrf_exempt, name="dispatch")
    def dispatch(self, request, *args: Any, **kwargs: Any):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, uidb64, token):
        """Verify token and activate account"""
        user_model = get_user_model()
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = user_model.objects.get(id=uid)
        except (TypeError, ValueError, OverflowError, user_model.DoesNotExist) as e:
            logger.error(e)
            user = None

        if user and token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return JsonResponse({}, status=200)
        else:
            return JsonResponse({}, status=422)
