# -*- coding: utf-8 -*-
from json import loads
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.mail import EmailMultiAlternatives
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy as r
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from loguru import logger

from bd_api.apps.account.signals import send_activation_email
from bd_api.apps.account.token import token_generator


class AccountActivateView(View):
    @method_decorator(csrf_exempt, name="dispatch")
    def dispatch(self, request, *args: Any, **kwargs: Any):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, uidb64):
        """Send activation account email"""
        user_model = get_user_model()
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = user_model.objects.get(id=uid)
        except (TypeError, ValueError, OverflowError, user_model.DoesNotExist) as e:
            logger.error(e)
            user = None

        if user:
            send_activation_email(user)
            return JsonResponse({}, status=200)
        else:
            return JsonResponse({}, status=422)


class AccountActivateConfirmView(View):
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
            from_email = settings.EMAIL_HOST_USER
            subject = "Base dos Dados: Redefinição de Senha"

            token = token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            content = render_to_string(
                "account/password_reset_email.html",
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
