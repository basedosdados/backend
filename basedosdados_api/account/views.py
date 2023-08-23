# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
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
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy as r
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.generic import CreateView

from basedosdados_api.account.forms import RegisterForm
from basedosdados_api.account.token import account_activation_token


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


class PasswordResetConfirmView(SuccessMessageMixin, PasswordResetConfirmView):
    template_name = "account/password_reset_confirm.html"
    success_message = "Sua senha foi alterada com sucesso."
    success_url = r("home")


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
                "token": account_activation_token.make_token(user),
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


class ActivateAccount(View):
    def get(self, request, uidb64, token):
        user_model = get_user_model()
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = user_model.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, user_model.DoesNotExist):
            user = None

        if user is not None and account_activation_token.check_token(user, token):
            user.is_active = True
            user.save()
            login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("home")
        else:
            return redirect("home")
