# -*- coding: utf-8 -*-
from json import loads
from typing import Any
import secrets

from graphql_jwt.shortcuts import get_token

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.mail import EmailMultiAlternatives
from django.http import JsonResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy as r
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from loguru import logger
import requests

from backend.apps.account.signals import send_activation_email
from backend.apps.account.token import token_generator
from backend.custom.environment import get_frontend_url


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
                    "name": user.get_full_name(),
                    "domain": get_frontend_url(),
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

class GoogleAuthView(View):
    """View para iniciar o fluxo de autenticação Google OAuth"""

    @method_decorator(csrf_exempt, name="dispatch")
    def dispatch(self, request, *args: Any, **kwargs: Any):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """Inicia o fluxo de autenticação Google OAuth"""
        try:
            state = secrets.token_urlsafe(32)
            request.session['oauth_state'] = state

            auth_url = (
                "https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={settings.GOOGLE_OAUTH_CLIENT_ID}&"
                f"redirect_uri={settings.BACKEND_URL}/account/google/callback/&"
                f"scope=openid email profile&"
                f"response_type=code&"
                f"state={state}&"
                f"access_type=offline&"
                f"include_granted_scopes=true"
            )
            return HttpResponseRedirect(auth_url)
        except Exception as e:
            logger.error(f"Erro ao iniciar autenticação Google: {e}")
            return JsonResponse({"error": "Erro interno do servidor"}, status=500)


class GoogleCallbackView(View):
    """View para processar o callback do Google OAuth"""

    @method_decorator(csrf_exempt, name="dispatch")
    def dispatch(self, request, *args: Any, **kwargs: Any):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """Processa o callback do Google OAuth"""
        try:
            auth_code = request.GET.get('code')
            state = request.GET.get('state')
            error = request.GET.get('error')

            if error:
                logger.error(f"Erro do Google OAuth: {error}")
                return JsonResponse({"error": f"Erro de autorização: {error}"}, status=400)

            if not auth_code:
                logger.error("Código de autorização não fornecido")
                return JsonResponse({"error": "Código de autorização não fornecido"}, status=400)

            if not state or state != request.session.get('oauth_state'):
                logger.error("Estado inválido - possível ataque CSRF")
                return JsonResponse({"error": "Estado inválido"}, status=400)

            if 'oauth_state' in request.session:
                del request.session['oauth_state']

            token_data = self._exchange_code_for_token(auth_code)
            if not token_data:
                logger.error("Falha ao trocar código por token")
                error_url = f"{settings.FRONTEND_URL}/user/login?error=auth_failed"
                return HttpResponseRedirect(error_url)

            user_info = self._get_user_info(token_data['access_token'])
            if not user_info:
                logger.error("Não foi possível obter informações do usuário")
                error_url = f"{settings.FRONTEND_URL}/user/login?error=user_info_failed"
                return HttpResponseRedirect(error_url)

            account = self._create_or_update_account(user_info, token_data.get('id_token'))

            if account:
                jwt_token = get_token(account)
                frontend_url = f"{settings.FRONTEND_URL}/user/login?login=success&token={jwt_token}&id={account.id}"
                return HttpResponseRedirect(frontend_url)
            else:
                logger.error("Erro ao criar/atualizar conta")
                error_url = f"{settings.FRONTEND_URL}/user/login?error=account_creation_failed"
                return HttpResponseRedirect(error_url)

        except Exception as e:
            logger.error(f"Erro no callback Google OAuth: {e}")
            error_url = f"{settings.FRONTEND_URL}/user/login?error=internal_server_error"
            return HttpResponseRedirect(error_url)

    def _exchange_code_for_token(self, auth_code):
        """Troca código de autorização por token de acesso"""
        try:
            token_url = "https://oauth2.googleapis.com/token"

            data = {
                'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
                'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': f"{settings.BACKEND_URL}/account/google/callback/"
            }

            response = requests.post(token_url, data=data)
            response.raise_for_status()

            token_data = response.json()
            logger.info("Token obtido com sucesso")

            return token_data

        except requests.RequestException as e:
            error_details = e.response.json() if e.response else str(e)
            logger.error(f"Erro ao trocar código por token: {error_details}")
            return None

    def _get_user_info(self, access_token):
        """Obtém informações do usuário do Google usando token de acesso"""
        try:
            userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {'Authorization': f'Bearer {access_token}'}

            response = requests.get(userinfo_url, headers=headers)
            response.raise_for_status()

            user_info = response.json()
            logger.info(f"Informações do usuário obtidas: {user_info.get('email')}")

            return user_info

        except requests.RequestException as e:
            error_details = e.response.json() if e.response else str(e)
            logger.error(f"Erro ao obter informações do usuário: {error_details}")
            return None

    def _create_or_update_account(self, user_info, id_token=None):
        """Cria nova conta ou atualiza conta existente com dados do Google"""
        try:
            user_model = get_user_model()
            email = user_info.get('email')
            google_sub = user_info.get('id')

            if not email or not google_sub:
                logger.error("Email ou Google Sub não fornecidos")
                return None

            name_parts = user_info.get('name', '').split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            username = email.split('@')[0]
            counter = 1
            original_username = username
            while user_model.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1

            account, created = user_model.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'google_sub': google_sub,
                    'is_active': True,
                }
            )

            if created:
                logger.info(f"Nova conta criada para {email}")
            else:
                logger.info(f"Conta Existente encontrada: {email}")
                if not account.google_sub:
                    account.google_sub = google_sub
                    logger.info(f"Conta {email} vinculada ao Google Sub")

                account.is_active = True
                account.save()

            return account

        except Exception as e:
            logger.error(f"Erro ao criar/atualizar conta: {e}")
            return None
