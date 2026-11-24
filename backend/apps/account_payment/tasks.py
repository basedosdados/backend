# -*- coding: utf-8 -*-
from google.auth.exceptions import RefreshError
from huey import crontab
from huey.contrib.djhuey import db_periodic_task
from loguru import logger

from backend.apps.account_payment.google_group import audit_google_group
from backend.apps.account_payment.webhooks import alert_google_credentials
from backend.custom.client import send_discord_message as send
from backend.custom.environment import production_task

logger = logger.bind(module="payment")

MAX_LISTED = 15


@db_periodic_task(crontab(hour="6", minute="0"))
@production_task
def audit_google_group_task():
    """Check daily that the BD Pro Google Group matches Stripe and the database.

    Reports to Discord; changes nothing. To fix, run
    `python manage.py audit_google_group --fix` in the API pod.
    """
    try:
        audit = audit_google_group()
    except RefreshError as e:
        return alert_google_credentials(e, "[google_group_audit] ")

    logger.bind(
        google_group_audit_missing=len(audit.missing),
        google_group_audit_stale=len(audit.stale),
        google_group_audit_inactive=len(audit.inactive),
        google_group_audit_unlinked=len(audit.unlinked),
        google_group_audit_extra=len(audit.extra),
    ).log(
        "INFO" if audit.ok else "WARNING",
        f"Auditoria do Google Group: {len(audit.missing)} faltando, "
        f"{len(audit.stale)} ativas só no banco, {len(audit.inactive)} pagas e inativas "
        f"no banco, {len(audit.unlinked)} pagas sem registro no banco, "
        f"{len(audit.extra)} sobrando",
    )
    if audit.ok:
        return

    lines = ["Auditoria do Google Group do BD Pro encontrou divergências."]
    if audit.missing:
        lines.append(f"\nCom assinatura ativa e fora do grupo ({len(audit.missing)}):")
        lines += [f"- {email}" for email, _, _ in audit.missing[:MAX_LISTED]]
    if audit.stale:
        lines.append(f"\nAtivas no banco, mas não no Stripe ({len(audit.stale)}):")
        lines += [f"- {email} (Stripe: {status})" for email, _, status in audit.stale[:MAX_LISTED]]
    if audit.inactive:
        lines.append(f"\nPagas no Stripe, mas inativas no banco ({len(audit.inactive)}):")
        lines += [
            f"- {email} (Stripe: {status})" for email, _, status in audit.inactive[:MAX_LISTED]
        ]
    if audit.unlinked:
        lines.append(f"\nPagas no Stripe, sem assinatura no banco ({len(audit.unlinked)}):")
        lines += [f"- {label} ({sub_id})" for label, sub_id in audit.unlinked[:MAX_LISTED]]
    lines.append("\nPara corrigir: `python manage.py audit_google_group --fix`")
    send("\n".join(lines))
