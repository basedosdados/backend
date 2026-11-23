# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from google.auth.exceptions import RefreshError

from backend.apps.account_payment.google_group import add_missing_members, audit_google_group


class Command(BaseCommand):
    help = (
        "Compara o Google Group do BD Pro com as assinaturas ativas no banco. "
        "Também serve para testar a credencial do Google: se ela for inválida, o comando falha."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Adiciona ao grupo quem tem assinatura ativa e está faltando.",
        )
        parser.add_argument(
            "--show-extra",
            action="store_true",
            help="Lista quem está no grupo sem assinatura ativa no banco (sem remover).",
        )

    def handle(self, *args, fix=False, show_extra=False, **options):
        try:
            audit = audit_google_group()
        except RefreshError as e:
            raise CommandError(
                "Credencial do Google inválida (chave da service account ou delegação "
                f"domain-wide): {e}"
            )

        self.stdout.write(
            f"Credencial do Google OK. Membros no grupo: {len(audit.members)}. "
            f"Esperados pelo banco: {len(audit.expected)}."
        )

        self.stdout.write(f"\nFaltando no grupo: {len(audit.missing)}")
        for email, account_id, subscription_id in audit.missing:
            self.stdout.write(f"  {email} (account {account_id}, subscription {subscription_id})")

        self.stdout.write(f"\nAtivas no banco, mas não no Stripe: {len(audit.stale)}")
        for email, subscription_id, status in audit.stale:
            self.stdout.write(f"  {email} (subscription {subscription_id}, Stripe: {status})")

        self.stdout.write(f"\nNo grupo sem assinatura ativa no banco: {len(audit.extra)}")
        if show_extra:
            for email in audit.extra:
                self.stdout.write(f"  {email}")

        if fix and audit.missing:
            failures = add_missing_members(audit)
            added = len(audit.missing) - len(failures)
            self.stdout.write(self.style.SUCCESS(f"\nAdicionados: {added}"))
            for email, error in failures:
                self.stderr.write(f"  Falhou {email}: {error}")
