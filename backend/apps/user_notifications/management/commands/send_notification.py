# -*- coding: utf-8 -*-

from collections import defaultdict

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone as dj_timezone

from backend.apps.user_notifications.models import Account, TableUpdateSubscription
from backend.custom.environment import get_frontend_url


def check_for_updates(subscription: TableUpdateSubscription) -> TableUpdateSubscription | bool:
    table = subscription.table

    if subscription.updated_at < table.last_updated_at:
        return subscription
    return False


def send_update_notification_email(user: Account, subscriptions: list, date_today: dj_timezone):
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]

    subject = "Atualização disponível para sua tabela de interesse"
    message = (
        f"Olá {user.username}, \n\nHá atualizações disponíveis para uma das tabelas que você segue."
    )

    content = render_to_string(
        "notification/update_table_notification.html",
        {"domain": get_frontend_url(), "subscriptions": subscriptions},
    )

    msg = EmailMultiAlternatives(subject, message, from_email, recipient_list)
    msg.attach_alternative(content, "text/html")
    msg.send()

    for subscription in subscriptions:
        subscription.last_notification = date_today
        subscription.updated_at = subscription.table.last_updated_at
        subscription.save()


class Command(BaseCommand):
    help = "Botão para testar o envio de emails"

    def handle(self, *args, **options):
        # Pegar
        self.check_for_updates_and_send_emails()

        self.stdout.write(self.style.SUCCESS('Successfully "check_for_updates_and_send_emails"'))

    def check_for_updates_and_send_emails(self):
        # Pega todas as inscrições ativas
        subscriptions = TableUpdateSubscription.objects.filter(status=True)
        # Pega a data atual
        date_today = dj_timezone.now()

        users_to_notify = defaultdict(list)
        # Lista de usuários que precisam receber o email e agrupada eles

        for subscription in subscriptions:
            if check_for_updates(subscription):
                users_to_notify[subscription.user].append(subscription)

        self.stdout.write(
            self.style.SUCCESS(f"Serão enviados um total de {len(users_to_notify.keys())} emails")
        )

        # Envia e-mail para cada usuário que precisa ser notificado
        for user, subscriptions_for_user in users_to_notify.items():
            send_update_notification_email(user, subscriptions_for_user, date_today)
