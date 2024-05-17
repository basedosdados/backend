# -*- coding: utf-8 -*-
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from bd_api.apps.account.models import Account, Subscription
from bd_api.apps.account.token import token_generator
from bd_api.custom.environment import get_frontend_url


def send_activation_email(account: Account):
    """Send activation email to account"""
    to_email = account.email
    from_email = settings.EMAIL_HOST_USER
    subject = "Bem Vindo à Base dos Dados!"

    token = token_generator.make_token(account)
    uid = urlsafe_base64_encode(force_bytes(account.pk))

    content = render_to_string(
        "account/activation_email.html",
        {
            "name": account.get_full_name(),
            "domain": get_frontend_url(),
            "uid": uid,
            "token": token,
        },
    )

    msg = EmailMultiAlternatives(subject, "", from_email, [to_email])
    msg.attach_alternative(content, "text/html")
    msg.send()


@receiver(post_save, sender=Account)
def send_activation_email_signal(sender, instance, created, raw, **kwargs):
    """Send activation email to instance after registration

    It only sends the email if:
    - The account is new
    - The account isn't active
    - The account isn't a fixture
    """
    if created and not raw and not instance.is_active:
        send_activation_email(instance)


def send_welcome_email(account: Account):
    """Send welcome email to account"""
    to_email = account.email
    from_email = settings.EMAIL_HOST_USER
    subject = "Bem Vindo à Base dos Dados!"

    token = token_generator.make_token(account)
    uid = urlsafe_base64_encode(force_bytes(account.pk))

    content = render_to_string(
        "account/welcome_email.html",
        {
            "name": account.get_full_name(),
            "domain": get_frontend_url(),
            "uid": uid,
            "token": token,
        },
    )

    msg = EmailMultiAlternatives(subject, "", from_email, [to_email])
    msg.attach_alternative(content, "text/html")
    msg.send()


def send_welcome_email_to_previous_subscribers():
    """Send welcome email to all previous subscribers"""

    for subscription in Subscription.objects.filter(
        subscription__status="active",
        subscription__created__lte=datetime(2023, 12, 1),
    ).all():
        send_welcome_email(subscription.admin)
