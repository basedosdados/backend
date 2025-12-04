# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.utils import timezone as dj_timezone

from backend.apps.user_notifications.models import TableUpdateSubscription


def check_for_updates(subscription: TableUpdateSubscription) -> TableUpdateSubscription | bool:
    table = subscription.table

    if subscription.updated_at < table.last_updated_at:
        return subscription
    return False


def send_update_notification_email(subscription: TableUpdateSubscription, date_today: dj_timezone):
    user = subscription.user
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]

    subject = "Atualização disponível para sua tabela de interesse"
    message = (
        f"Olá {user.username}, \n\nHá atualizações disponíveis para uma das tabelas que você segue."
    )

    # content = render_to_string(
    #     "account/activation_email.html",
    #     {
    #         "name": user.get_full_name(),
    #         "domain": get_frontend_url(),
    #     },
    # )

    msg = EmailMultiAlternatives(subject, message, from_email, recipient_list)
    # msg.attach_alternative(content, "text/html")
    msg.send()

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

        # Lista de usuários que precisam receber o email
        subscriptions = [check_for_updates(subscription) for subscription in subscriptions]

        users_to_notify = [subscription for subscription in subscriptions if subscription]
        # Envia e-mail para cada usuário que precisa ser notificado
        self.stdout.write(
            self.style.SUCCESS(f"Serão enviados um total de {len(users_to_notify)} emails")
        )
        for subscription in subscriptions:
            if subscription:
                send_update_notification_email(subscription, date_today)
