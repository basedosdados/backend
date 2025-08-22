# -*- coding: utf-8 -*-
from django.conf import settings
from djstripe import webhooks
from djstripe.models import Event
from djstripe.models import Subscription as DJStripeSubscription
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from loguru import logger
from stripe import Customer as StripeCustomer
from stripe import Subscription as StripeSubscription
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist

from backend.apps.account.models import Account, Subscription
from backend.custom.client import send_discord_message as send
from backend.custom.environment import get_backend_url

logger = logger.bind(module="payment")


def get_subscription(event: Event) -> Subscription:
    """Get internal subscription model, mirror of stripe"""
    logger.info(f"Procurando inscrição interna do cliente {event.customer.email}")
    subscription = DJStripeSubscription.objects.get(id=event.data["object"]["id"])
    internal_subscription = Subscription.objects.filter(subscription=subscription).first()

    if internal_subscription:
        logger.info(f"Retornando inscrição interna do cliente {event.customer.email}")
        return internal_subscription
    else:
        if event.customer.subscriber:
            logger.info(f"Criando inscrição interna do cliente {event.customer.email}")
            return Subscription.objects.create(
                subscription=subscription,
                admin=event.customer.subscriber,
            )


def get_credentials(scopes: list[str] = None, impersonate: str = None):
    """Get google credentials with scope or subject"""
    cred = Credentials.from_service_account_file(
        settings.GOOGLE_APPLICATION_CREDENTIALS,
    )
    if scopes:
        cred = cred.with_scopes(scopes)
    if impersonate:
        cred = cred.with_subject(impersonate)
    return cred


def get_service() -> Resource:
    """Get google directory service"""
    credentials = get_credentials(
        settings.GOOGLE_DIRECTORY_SCOPES,
        settings.GOOGLE_DIRECTORY_SUBJECT,
    )
    return build("admin", "directory_v1", credentials=credentials)


def add_user(email: str, group_key: str = None, role: str = "MEMBER"):
    """Add user to google group"""
    if not group_key:
        group_key = settings.GOOGLE_DIRECTORY_GROUP_KEY
    if "+" in email and email.index("+") < email.index("@"):
        email = email.split("+")[0] + "@" + email.split("@")[1]
    try:
        service = get_service()
        service.members().insert(
            groupKey=group_key,
            body={"email": email, "role": role},
        ).execute()
    except HttpError as e:
        if e.resp.status == 409:
            logger.warning(f"{email} já existe no google groups")
        else:
            send(f"Verifique o erro ao adicionar o usuário ao google groups: {e}")
            logger.error(e)
            raise e

def _normalize_plus(email: str) -> str:
    """Normaliza: trim, lower e remove +alias antes do @."""
    email = email.strip().lower()
    local, _, domain = email.partition("@")
    if "+" in local:
        local = local.split("+", 1)[0]
    return f"{local}@{domain}"

def remove_user(email: str, group_key: str = None) -> None:
    """Remove user from google group, exceto emails internos basedosdados.org"""
    if not email or "@" not in email:
        logger.error(f"E-mail inválido fornecido: {email!r}")
        return

    raw_email = email.strip().lower()

    if raw_email.endswith("@basedosdados.org"):
        logger.warning(f"Bloqueado: {raw_email} é email interno. Não removido do Google Groups.")
        return

    base_email = _normalize_plus(raw_email)
    group_key = group_key or settings.GOOGLE_DIRECTORY_GROUP_KEY

    try:
        service = get_service()
        service.members().delete(
            groupKey=group_key,
            memberKey=base_email,
        ).execute()
    except HttpError as e:
        if e.resp.status == 404:
            logger.warning(f"{base_email} já foi removido do Google Groups")
        else:
            send(f"Verifique o erro ao remover '{base_email}' do Google Groups: {e}")
            logger.error(e)
            raise
    except Exception:
        logger.exception(f"Erro inesperado ao remover {base_email} do Google Groups")
        raise


def list_user(group_key: str = None):
    """List users from google group"""
    if not group_key:
        group_key = settings.GOOGLE_DIRECTORY_GROUP_KEY
    try:
        service = get_service()
        return service.members().list(groupKey=group_key).execute()
    except Exception as e:
        logger.error(e)
        raise e


def is_email_in_group(email: str, group_key: str = None) -> bool:
    """Check if a user is in a Google group."""
    if not group_key:
        group_key = settings.GOOGLE_DIRECTORY_GROUP_KEY
    if "+" in email and email.index("+") < email.index("@"):
        email = email.split("+")[0] + "@" + email.split("@")[1]

    try:
        service = get_service()
        response = (
            service.members()
            .get(
                groupKey=group_key,
                memberKey=email.lower(),
            )
            .execute()
        )

        member_email = response.get("email")
        if not member_email:
            return False

        return member_email.lower() == email.lower()
    except HttpError as e:
        logger.error(f"Erro ao verificar o usuário {email} no grupo {group_key}: {e}")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao verificar o usuário {email}: {e}")
        raise e


@webhooks.handler("customer.updated")
def update_customer(event: Event, **kwargs):
    """Propagate customer email update if exists"""
    account = event.customer.subscriber
    if account and account.email != event.data["object"]["email"]:
        logger.info(f"Atualizando o email do cliente {event.customer.email}")
        account.email = event.data["object"]["email"]
        account.save(update_fields=["email"])


def handle_subscription(event: Event):
    """Handle subscription status"""
    subscription = get_subscription(event)
    account = Account.objects.filter(email=event.customer.email).first()

    if event.data["object"]["status"] in ["trialing", "active"]:
        if subscription:
            logger.info(f"Adicionando a inscrição do cliente {event.customer.email}")
            subscription.is_active = True
            subscription.save()

        # Add user to google group if subscription exists or not
        if account:
            add_user(account.gcp_email or account.email)
        else:
            add_user(event.customer.email)
    else:
        if subscription:
            logger.info(f"Removendo a inscrição do cliente {event.customer.email}")
            subscription.is_active = False
            subscription.save()
        # Remove user from google group if subscription exists or not
        try:
            if account:
                remove_user(account.gcp_email or account.email)
            else:
                remove_user(event.customer.email)
        except Exception as e:
            logger.error(e)


@webhooks.handler("customer.subscription.updated")
def subscription_updated(event: Event, **kwargs):
    """Handle subscription status update"""
    handle_subscription(event)


@webhooks.handler("customer.subscription.created")
def subscribe(event: Event, **kwargs):
    """Add customer to allowed google groups"""
    handle_subscription(event)


@webhooks.handler("customer.subscription.deleted")
def unsubscribe(event: Event, **kwargs):
    """Remove customer from allowed google groups"""
    if subscription := get_subscription(event):
        logger.info(f"Removendo a inscrição do cliente {event.customer.email}")
        subscription.is_active = False
        subscription.save()

    account = Account.objects.filter(email=event.customer.email).first()
    # Remove user from google group if subscription exists or not
    try:
        if account:
            remove_user(account.gcp_email or account.email)
        else:
            remove_user(event.customer.email)
    except Exception as e:
        logger.error(e)


@webhooks.handler("customer.subscription.paused")
def pause_subscription(event: Event, **kwargs):
    """Pause customer subscription"""
    account = Account.objects.filter(email=event.customer.email).first()

    if subscription := get_subscription(event):
        logger.info(f"Pausando a inscrição do cliente {event.customer.email}")
        subscription.is_active = False
        subscription.save()

    try:
        if account:
            remove_user(account.gcp_email or account.email)
        else:
            remove_user(event.customer.email)
    except Exception as e:
        logger.error(e)


@webhooks.handler("customer.subscription.resumed")
def resume_subscription(event: Event, **kwargs):
    """Resume customer subscription"""
    account = Account.objects.filter(email=event.customer.email).first()

    if subscription := get_subscription(event):
        logger.info(f"Resumindo a inscrição do cliente {event.customer.email}")
        subscription.is_active = True
        subscription.save()

    try:
        if account:
            add_user(account.gcp_email or account.email)
        else:
            add_user(event.customer.email)
    except Exception as e:
        logger.error(e)


@webhooks.handler("setup_intent.succeeded")
def setup_intent_succeeded(event: Event, **kwargs):
    """Update customer default payment method and subscribe to plan with trial"""
    logger.info(f"Setup intent updated {event.customer.email}")

    customer = event.customer
    setup_intent = event.data["object"]
    metadata = setup_intent.get("metadata")
    price_id = metadata.get("price_id")
    promotion_code = metadata.get("promotion_code")
    backend_url = metadata.get("backend_url")

    if not backend_url == get_backend_url():
        return logger.info(f"Ignore setup intent from {backend_url}")

    StripeCustomer.modify(
        customer.id,
        invoice_settings={"default_payment_method": setup_intent.get("payment_method")},
    )

    subscriptions = StripeSubscription.list(customer=customer.id)
    has_subscription = len(subscriptions.get("data")) > 0

    if promotion_code:
        discounts = [{"promotion_code": promotion_code}]
    else:
        discounts = []

    if not has_subscription and price_id:
        logger.info(f"Add subscription to user {event.customer.email}")
        customer.subscribe(price=price_id, trial_period_days=7, discounts=discounts)


# Reference
# https://developers.google.com/admin-sdk/directory/v1/guides/troubleshoot-error-codes
# https://developers.google.com/admin-sdk/reseller/v1/support/directory_api_common_errors
