# -*- coding: utf-8 -*-
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from app.account.models import Account
from app.account.token import token_generator
from app.settings import EMAIL_HOST_USER


@receiver(post_save, sender=Account)
def send_activation_email(sender, instance, created, raw, **kwargs):
    """Send activation email to instance after registration

    It only sends the email if:
    - The account is new
    - The account isn't active
    - The account isn't a fixture
    """
    if created and not raw and not instance.is_active:
        to_email = instance.email
        from_email = EMAIL_HOST_USER
        subject = "Bem Vindo à Base dos Dados!"

        token = token_generator.make_token(instance)
        uid = urlsafe_base64_encode(force_bytes(instance.pk))

        content = render_to_string(
            "account/activation_email_v1.html",
            {
                "name": instance.full_name,
                "domain": "basedosdados.org",
                "uid": uid,
                "token": token,
            },
        )

        msg = EmailMultiAlternatives(subject, "", from_email, [to_email])
        msg.attach_alternative(content, "text/html")
        msg.send()
