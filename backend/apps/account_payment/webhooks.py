# -*- coding: utf-8 -*-
from django.conf import settings
from django.db.models import Q
from djstripe import webhooks
from djstripe.models import Event
from djstripe.models import Subscription as DJStripeSubscription
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from loguru import logger
from stripe import Customer as StripeCustomer
from stripe import Subscription as StripeSubscription

from backend.apps.account.models import Account, Subscription
from backend.custom.client import send_discord_message as send
from backend.custom.environment import get_backend_url, is_dev, is_stg

logger = logger.bind(module="payment")


def _normalize_plus(email: str) -> str:
    """Normaliza: trim, lower e remove +alias antes do @."""
    email = email.strip().lower()
    local, _, domain = email.partition("@")
    if "+" in local:
        local = local.split("+", 1)[0]
    return f"{local}@{domain}"


def get_subscription(event: Event, event_context: str = None) -> Subscription:
    """Get internal subscription model, mirror of stripe"""
    ctx = f"[{event_context}] " if event_context else ""
    subscription_id = event.data.get("object", {}).get("id")
    if not subscription_id:
        return None

    logger.info(f"{ctx}Procurando inscrição interna do cliente {event.customer.email}")

    try:
        subscription = DJStripeSubscription.objects.get(id=subscription_id)
    except DJStripeSubscription.DoesNotExist:
        return None

    internal_subscription = Subscription.objects.filter(subscription=subscription).first()

    if internal_subscription:
        logger.info(f"{ctx}Retornando inscrição interna do cliente {event.customer.email}")
        return internal_subscription
    else:
        if getattr(event.customer, "subscriber", None):
            logger.info(f"{ctx}Criando inscrição interna do cliente {event.customer.email}")
            return Subscription.objects.create(
                subscription=subscription,
                admin=event.customer.subscriber,
            )


def get_product_slug(subscription_model=None, event=None, event_context: str = None) -> str:
    ctx = f"[{event_context}] " if event_context else ""
    try:
        djstripe_sub = None
        if subscription_model and getattr(subscription_model, "subscription", None):
            djstripe_sub = subscription_model.subscription
        elif event:
            sub_id = event.data.get("object", {}).get("id")
            if sub_id:
                djstripe_sub = DJStripeSubscription.objects.filter(id=sub_id).first()

        if djstripe_sub:
            if getattr(djstripe_sub, "plan", None) and getattr(djstripe_sub.plan, "product", None):
                return djstripe_sub.plan.product.metadata.get("code", "")
            elif hasattr(djstripe_sub, "items") and djstripe_sub.items.first():
                item = djstripe_sub.items.first()
                if getattr(item, "price", None) and getattr(item.price, "product", None):
                    return item.price.product.metadata.get("code", "")
    except Exception as e:
        logger.error(f"{ctx}Erro ao recuperar product slug da assinatura: {e}")
    return ""


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


def add_user(
    email: str,
    account: Account = None,
    group_key: str = None,
    role: str = "MEMBER",
    event_context: str = None,
):
    """Add user to google group"""
    ctx = f"[{event_context}] " if event_context else ""
    if is_dev() or is_stg():
        if account is None:
            normalized_email = _normalize_plus(email)
            account = Account.objects.filter(
                Q(email__iexact=email) | Q(email__iexact=normalized_email)
            ).first()

        if not (account and account.is_admin):
            logger.info(
                f"{ctx}Ignorando adição do usuário '{email}' "
                "em ambiente de dev/staging pois não é admin."
            )
            return

    if not group_key:
        group_key = settings.GOOGLE_DIRECTORY_GROUP_KEY
    email = _normalize_plus(email)
    try:
        service = get_service()
        service.members().insert(
            groupKey=group_key,
            body={"email": email, "role": role},
        ).execute()
    except HttpError as e:
        if e.resp.status == 409:
            logger.warning(f"{ctx}{email} já existe no google groups")
        else:
            send(f"Verifique o erro ao adicionar o usuário ao google groups: {e}")
            logger.error(f"{ctx}{e}")
            raise e


def remove_user(email: str, group_key: str = None, event_context: str = None) -> None:
    """Remove user from Google Group"""
    ctx = f"[{event_context}] " if event_context else ""
    if not email or "@" not in email:
        logger.error(f"{ctx}E-mail inválido fornecido: {email!r}")
        return

    raw_email = email.strip().lower()
    base_email = _normalize_plus(raw_email)

    user = Account.objects.filter(
        Q(email__iexact=raw_email)
        | Q(email__iexact=base_email)
        | Q(gcp_email__iexact=raw_email)
        | Q(gcp_email__iexact=base_email)
    ).first()

    if not user:
        logger.warning(
            f"{ctx}Usuário {raw_email} não encontrado no banco. "
            "Tentando remoção direta do Google Group."
        )

    if user:
        if user.is_admin:
            logger.warning(f"{ctx}Bloqueado: {raw_email} é admin. Não removido do Google Groups.")
            return

        has_active_sub = (
            getattr(user, "is_subscriber", False)
            or DJStripeSubscription.objects.filter(
                customer__subscriber=user, status__in=["active", "trialing"]
            ).exists()
        )

        if has_active_sub:
            logger.warning(
                f"{ctx}Bloqueado: {raw_email} possui uma assinatura ativa. "
                "Não removido do Google Groups."
            )
            return

    group_key = group_key or settings.GOOGLE_DIRECTORY_GROUP_KEY

    try:
        service = get_service()
        service.members().delete(
            groupKey=group_key,
            memberKey=base_email,
        ).execute()
    except HttpError as e:
        try:
            status_code = int(getattr(e.resp, "status", None) or 0)
        except Exception:
            status_code = 0

        if status_code == 404 or status_code == 400:
            logger.warning(
                f"{ctx}{base_email} não encontrado no Google Groups (já removido ou chave inválida)"
            )
            return

        send(f"Verifique o erro ao remover '{base_email}' do Google Groups: {e}")
        logger.error(f"{ctx}{e}")
        raise
    except Exception as e:
        logger.exception(f"{ctx}Erro inesperado ao remover {base_email} do Google Groups: {e}")
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

    email = _normalize_plus(email)

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
    if not getattr(event, "customer", None):
        return

    account = event.customer.subscriber
    new_email = event.data.get("object", {}).get("email")
    if account and new_email and account.email != new_email:
        logger.info(
            f"[Webhook: {event.type} | Event ID: {event.id}] "
            f"Atualizando o email do cliente {event.customer.email}"
        )
        account.email = new_email
        account.save(update_fields=["email"])


def handle_subscription(event: Event):
    """Handle subscription status"""
    if not getattr(event, "customer", None) or not getattr(event.customer, "email", None):
        logger.warning(f"Webhook {event.type} abortado: cliente ou e-mail ausente.")
        return

    event_context = f"Webhook: {event.type} | Event ID: {event.id}"
    ctx = f"[{event_context}] "

    subscription = get_subscription(event, event_context=event_context)
    account = Account.objects.filter(email=event.customer.email).first()

    status = event.data.get("object", {}).get("status")
    is_chatbot_plan = (
        get_product_slug(subscription, event, event_context=event_context) == "chatbot"
    )

    if status in ["trialing", "active"]:
        if subscription:
            logger.info(f"{ctx}Adicionando a inscrição do cliente {event.customer.email}")
            subscription.is_active = True
            subscription.save()

        # Add user to google group if subscription exists or not
        if account:
            if is_chatbot_plan:
                try:
                    logger.info(
                        f"{ctx}Liberando acesso ao chatbot para o cliente {event.customer.email}"
                    )
                    account.has_chatbot_access = True
                    account.save(update_fields=["has_chatbot_access"])
                except Exception as e:
                    logger.error(f"{ctx}{e}")
            else:
                add_user(
                    account.gcp_email or account.email, account=account, event_context=event_context
                )
        else:
            if not is_chatbot_plan:
                add_user(event.customer.email, account=None, event_context=event_context)
    else:
        if subscription:
            logger.info(
                f"{ctx}Removendo a inscrição do cliente {event.customer.email} "
                f"(Status via Stripe: {status})"
            )
            subscription.is_active = False
            subscription.save()
        # Remove user from google group if subscription exists or not
        if is_chatbot_plan and account:
            try:
                logger.info(
                    f"{ctx}Removendo acesso ao chatbot para o cliente {event.customer.email}"
                )
                account.has_chatbot_access = False
                account.save(update_fields=["has_chatbot_access"])
            except Exception as e:
                logger.error(f"{ctx}{e}")
        elif not is_chatbot_plan:
            try:
                if account:
                    remove_user(account.gcp_email or account.email, event_context=event_context)
                else:
                    remove_user(event.customer.email, event_context=event_context)
            except Exception as e:
                logger.error(f"{ctx}{e}")


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
    if not getattr(event, "customer", None) or not getattr(event.customer, "email", None):
        return

    event_context = f"Webhook: {event.type} | Event ID: {event.id}"
    ctx = f"[{event_context}] "

    if subscription := get_subscription(event, event_context=event_context):
        logger.info(f"{ctx}Removendo a inscrição do cliente {event.customer.email}")
        subscription.is_active = False
        subscription.save()

    account = Account.objects.filter(email=event.customer.email).first()
    is_chatbot_plan = (
        get_product_slug(subscription, event, event_context=event_context) == "chatbot"
    )

    if is_chatbot_plan and account:
        try:
            logger.info(f"{ctx}Removendo acesso ao chatbot para o cliente {event.customer.email}")
            account.has_chatbot_access = False
            account.save(update_fields=["has_chatbot_access"])
        except Exception as e:
            logger.error(f"{ctx}{e}")
    elif not is_chatbot_plan:
        # Remove user from google group if subscription exists or not
        try:
            if account:
                remove_user(account.gcp_email or account.email, event_context=event_context)
            else:
                remove_user(event.customer.email, event_context=event_context)
        except Exception as e:
            logger.error(f"{ctx}{e}")


@webhooks.handler("customer.subscription.paused")
def pause_subscription(event: Event, **kwargs):
    """Pause customer subscription"""
    if not getattr(event, "customer", None) or not getattr(event.customer, "email", None):
        return

    event_context = f"Webhook: {event.type} | Event ID: {event.id}"
    ctx = f"[{event_context}] "

    account = Account.objects.filter(email=event.customer.email).first()

    if subscription := get_subscription(event, event_context=event_context):
        logger.info(f"{ctx}Pausando a inscrição do cliente {event.customer.email}")
        subscription.is_active = False
        subscription.save()

    is_chatbot_plan = (
        get_product_slug(subscription, event, event_context=event_context) == "chatbot"
    )

    if is_chatbot_plan and account:
        try:
            logger.info(
                f"{ctx}Removendo acesso ao chatbot para o cliente {event.customer.email} (Pausado)"
            )
            account.has_chatbot_access = False
            account.save(update_fields=["has_chatbot_access"])
        except Exception as e:
            logger.error(f"{ctx}{e}")
    elif not is_chatbot_plan:
        try:
            if account:
                remove_user(account.gcp_email or account.email, event_context=event_context)
            else:
                remove_user(event.customer.email, event_context=event_context)
        except Exception as e:
            logger.error(f"{ctx}{e}")


@webhooks.handler("customer.subscription.resumed")
def resume_subscription(event: Event, **kwargs):
    """Resume customer subscription"""
    if not getattr(event, "customer", None) or not getattr(event.customer, "email", None):
        return

    event_context = f"Webhook: {event.type} | Event ID: {event.id}"
    ctx = f"[{event_context}] "

    account = Account.objects.filter(email=event.customer.email).first()

    if subscription := get_subscription(event, event_context=event_context):
        logger.info(f"{ctx}Resumindo a inscrição do cliente {event.customer.email}")
        subscription.is_active = True
        subscription.save()

    is_chatbot_plan = (
        get_product_slug(subscription, event, event_context=event_context) == "chatbot"
    )

    if is_chatbot_plan and account:
        try:
            logger.info(
                f"{ctx}Liberando acesso ao chatbot para o cliente {event.customer.email} (Resumido)"
            )
            account.has_chatbot_access = True
            account.save(update_fields=["has_chatbot_access"])
        except Exception as e:
            logger.error(f"{ctx}{e}")
    elif not is_chatbot_plan:
        try:
            if account:
                add_user(
                    account.gcp_email or account.email, account=account, event_context=event_context
                )
            else:
                add_user(event.customer.email, account=None, event_context=event_context)
        except Exception as e:
            logger.error(f"{ctx}{e}")


@webhooks.handler("setup_intent.succeeded")
def setup_intent_succeeded(event: Event, **kwargs):
    """Update customer default payment method and subscribe to plan with trial"""
    if not getattr(event, "customer", None):
        return

    ctx = f"[Webhook: {event.type} | Event ID: {event.id}] "
    logger.info(f"{ctx}Setup intent updated {event.customer.email}")

    customer = event.customer
    setup_intent = event.data.get("object", {})
    metadata = setup_intent.get("metadata", {})
    price_id = metadata.get("price_id")
    promotion_code = metadata.get("promotion_code")
    backend_url = metadata.get("backend_url")

    if not backend_url == get_backend_url():
        return logger.info(f"{ctx}Ignore setup intent from {backend_url}")

    payment_method = setup_intent.get("payment_method")
    if payment_method:
        StripeCustomer.modify(
            customer.id,
            invoice_settings={"default_payment_method": payment_method},
        )

    subscriptions = StripeSubscription.list(customer=customer.id)
    has_subscription = len(subscriptions.get("data", [])) > 0

    if promotion_code:
        discounts = [{"promotion_code": promotion_code}]
    else:
        discounts = []

    if not has_subscription and price_id:
        logger.info(f"{ctx}Add subscription to user {event.customer.email}")
        customer.subscribe(price=price_id, trial_period_days=7, discounts=discounts)


# Reference
# https://developers.google.com/admin-sdk/directory/v1/guides/troubleshoot-error-codes
# https://developers.google.com/admin-sdk/reseller/v1/support/directory_api_common_errors
