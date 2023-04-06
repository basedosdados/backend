# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model, authenticate, login
from django.urls import reverse_lazy as r

from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordChangeDoneView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView

from basedosdados_api.account.forms import RegisterForm


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
    success_message = "Enviamos um email com as istruções para você configurar uma nova senha, " \
                      "caso exista uma conta com o email formecido. Você deve recebê-lo em breve." \
                      " Se você não receber o email, " \
                      "verifique se você digitou o endereço correto e verifique sua caixa de spam."
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
        username = form.cleaned_data.get("username")
        password = form.cleaned_data.get("password1")
        user = form.save()
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        return response
