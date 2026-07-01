# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import NamedTuple

from django.conf import settings
from django.db.models import Q
from djstripe import webhooks
from djstripe.models import Event
from djstripe.models import Price as DJStripePrice
from djstripe.models import Subscription as DJStripeSubscription
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from loguru import logger
from stripe import Customer as StripeCustomer

from backend.apps.account.models import Account, Subscription
from backend.apps.account_payment.trials import (
    account_eligible_for_bdpro_stripe_trial,
    account_eligible_for_chatbot_stripe_trial,
    account_has_active_chatbot_stripe_subscription,
    djstripe_subscription_is_chatbot,
)
from backend.custom.client import send_discord_message as send
from backend.custom.environment import get_backend_url, is_dev, is_stg

logger = logger.bind(module="payment")


def _normalize_plus(email: str) -> str:
    """Normalize an email address for comparison and lookup.

    Trims whitespace, lowercases the address, and strips a `+alias` suffix
    from the local part (e.g. `user+test@example.com` -> `user@example.com`)
    so addresses with plus-aliasing still match the canonical account email.

    Args:
        email: Raw email address to normalize.

    Returns:
        The normalized email address.
    """
    email = email.strip().lower()
    local, _, domain = email.partition("@")
    if "+" in local:
        local = local.split("+", 1)[0]
    return f"{local}@{domain}"


def get_subscription(event: Event, event_context: str = None) -> Subscription | None:
    """Get (or lazily create) the internal Subscription mirroring a Stripe event.

    Looks up the DJStripeSubscription referenced by the event, then returns
    the internal `Subscription` model that mirrors it, creating it on first
    use if the Stripe customer has a known subscriber account.

    Args:
        event: Stripe webhook event whose `data.object.id` identifies the
            underlying Stripe subscription.
        event_context: Human-readable context prefixed to log messages.

    Returns:
        The internal `Subscription` instance, or `None` if the event has no
        subscription id, the DJStripeSubscription doesn't exist yet, or the
        Stripe customer has no associated subscriber account.
    """
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
    """Resolve the Stripe product `code` metadata for a subscription.

    Walks from an internal `Subscription` (or, failing that, from the
    event's underlying DJStripeSubscription) through its plan/price to the
    Stripe Product, returning the `code` value from the product's metadata.
    Used to distinguish products (e.g. "chatbot" vs "bd_pro") for
    entitlement routing.

    Args:
        subscription_model: Internal `Subscription` instance to resolve the
            product from, if available.
        event: Stripe webhook event to fall back to when `subscription_model`
            has no linked DJStripeSubscription.
        event_context: Human-readable context prefixed to log messages.

    Returns:
        The product's `code` metadata value, or `""` if it can't be resolved.
    """
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


class WebhookContext(NamedTuple):
    """Common context validated once per Stripe event.

    Bundles the event, a human-readable description, the formatted log
    prefix, and the customer's email so handlers don't need to re-derive or
    re-validate them.

    Attributes:
        event: The Stripe webhook event being processed.
        event_context: Human-readable description of the event (type + id).
        ctx: `event_context` formatted as a log-line prefix, e.g. `"[...] "`.
        customer_email: The Stripe customer's email address.
    """

    event: Event
    event_context: str
    ctx: str
    customer_email: str


def require_webhook_customer_context(
    event: Event,
    *,
    log_if_invalid: bool = False,
) -> WebhookContext | None:
    """Validate that an event has a Stripe customer with an email.

    Centralizes the customer/email guard that every subscription handler
    needs before doing any work, and builds the shared `WebhookContext` used
    for logging and entitlement routing.

    Args:
        event: The Stripe webhook event to validate.
        log_if_invalid: Whether to emit a warning log when the customer or
            email is missing.

    Returns:
        A populated `WebhookContext`, or `None` if the event has no customer
        or the customer has no email.
    """
    customer = getattr(event, "customer", None)
    email = getattr(customer, "email", None) if customer else None
    if not customer or not email:
        if log_if_invalid:
            logger.warning(f"Webhook {event.type} abortado: cliente ou e-mail ausente.")
        return None
    event_context = f"Webhook: {event.type} | Event ID: {event.id}"
    ctx = f"[{event_context}] "
    return WebhookContext(
        event=event,
        event_context=event_context,
        ctx=ctx,
        customer_email=email,
    )


def get_account_for_stripe_customer(event: Event) -> Account | None:
    """Look up the internal Account matching an event's Stripe customer.

    Args:
        event: Stripe webhook event whose `customer.email` identifies the
            account.

    Returns:
        The matching `Account`, or `None` if no account has that email.
    """
    return Account.objects.filter(email=event.customer.email).first()


def subscription_product_is_chatbot(
    subscription: Subscription | None,
    event: Event,
    event_context: str,
) -> bool:
    """Check whether a subscription's product is the chatbot product.

    Args:
        subscription: Internal `Subscription` instance, if available.
        event: Stripe webhook event to fall back to for product resolution.
        event_context: Human-readable context prefixed to log messages.

    Returns:
        `True` if the resolved product slug is exactly `"chatbot"`.
    """
    return get_product_slug(subscription, event, event_context=event_context) == "chatbot"


def _djstripe_subscription_is_chatbot(dj_sub: DJStripeSubscription) -> bool:
    return djstripe_subscription_is_chatbot(dj_sub)


def _account_has_other_active_chatbot_subscription(
    account: Account,
    exclude_stripe_subscription_id: str | None,
) -> bool:
    """True if the customer still has another active/trialing Stripe sub for the chatbot product."""
    return account_has_active_chatbot_stripe_subscription(
        account,
        exclude_stripe_subscription_id=exclude_stripe_subscription_id,
    )


def _account_has_active_non_chatbot_subscription(account: Account) -> bool:
    """Check if an account has an active/trialing non-chatbot subscription.

    Used by `remove_user` to decide whether an account should keep its
    Google Group membership: chatbot subscriptions don't grant Google Group
    access, so only non-chatbot (e.g. bd_pro) subscriptions should block
    removal.

    Args:
        account: The account whose Stripe subscriptions to check.

    Returns:
        `True` if at least one active/trialing non-chatbot subscription
        exists for the account's Stripe customer.
    """
    qs = DJStripeSubscription.objects.filter(
        customer__subscriber=account,
        status__in=["active", "trialing"],
    )
    return any(not _djstripe_subscription_is_chatbot(s) for s in qs.iterator(chunk_size=20))


def _price_is_chatbot(price_id: str) -> bool | None:
    """Check whether a Stripe Price belongs to the chatbot product.

    Args:
        price_id: Stripe price id (or dj-stripe internal id, as a fallback)
            to look up.

    Returns:
        `True`/`False` depending on whether the price's product `code`
        metadata contains `"chatbot"`, or `None` if the price (or its
        product) can't be found.
    """
    price = (
        DJStripePrice.objects.filter(id=price_id).first()
        or DJStripePrice.objects.filter(djstripe_id=price_id).first()
    )
    if not price or not getattr(price, "product", None):
        return None
    return "chatbot" in price.product.metadata.get("code", "").lower()


def _customer_has_active_subscription_of_type(customer, is_chatbot: bool) -> bool:
    """Check if a Stripe customer already has an active sub of a given type.

    Used by `setup_intent_succeeded` to avoid creating a duplicate
    subscription for the same product type (chatbot or bd_pro) while still
    allowing the customer to hold one of each.

    Args:
        customer: The dj-stripe `Customer` instance to check.
        is_chatbot: Whether to match chatbot subscriptions (`True`) or
            non-chatbot subscriptions (`False`).

    Returns:
        `True` if an active/trialing subscription of the requested type
        already exists for the customer.
    """
    qs = DJStripeSubscription.objects.filter(
        customer=customer,
        status__in=["active", "trialing"],
    )
    return any(
        _djstripe_subscription_is_chatbot(s) == is_chatbot for s in qs.iterator(chunk_size=20)
    )


def _set_account_chatbot_access(
    account: Account,
    enabled: bool,
    wc: WebhookContext,
    log_message: str,
) -> None:
    """Grant or revoke an account's chatbot access, protecting admins.

    Admin accounts are never automatically stripped of chatbot access by a
    webhook; a revocation attempt for an admin is logged and skipped.

    Args:
        account: The account to update.
        enabled: `True` to grant chatbot access, `False` to revoke it.
        wc: Context for the originating webhook event, used for logging.
        log_message: Message to log when the change is applied.
    """
    try:
        if not enabled and account.is_admin:
            logger.warning(
                f"{wc.ctx}Bloqueado: {account.email} é admin. Acesso ao chatbot não removido."
            )
            return
        logger.info(f"{wc.ctx}{log_message}")
        account.has_chatbot_access = enabled
        account.save(update_fields=["has_chatbot_access"])
    except Exception as e:
        logger.error(f"{wc.ctx}{e}")


def get_credentials(scopes: list[str] = None, impersonate: str = None):
    """Build Google service-account credentials.

    Args:
        scopes: OAuth scopes to request, if any.
        impersonate: Subject (user email) to impersonate via domain-wide
            delegation, if any.

    Returns:
        A `google.oauth2.service_account.Credentials` instance.
    """
    cred = Credentials.from_service_account_file(
        settings.GOOGLE_APPLICATION_CREDENTIALS,
    )
    if scopes:
        cred = cred.with_scopes(scopes)
    if impersonate:
        cred = cred.with_subject(impersonate)
    return cred


def get_service() -> Resource:
    """Build an authenticated Google Workspace Directory API client.

    Returns:
        A `Resource` for the `admin` `directory_v1` API, scoped and
        impersonating the subject configured in settings.
    """
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
    """Add a user to the Google Group used to gate BD Pro access.

    In dev/staging environments, only admin accounts are actually added, to
    avoid polluting the real Google Group from test events.

    Args:
        email: Email address to add to the group; normalized before use.
        account: Account associated with `email`, if already known. If not
            given, it's looked up by `email` (with +alias normalization)
            when running in dev/staging.
        group_key: Google Group key to add the member to. Defaults to
            `settings.GOOGLE_DIRECTORY_GROUP_KEY`.
        role: Google Group member role to assign.
        event_context: Human-readable context prefixed to log messages.

    Raises:
        HttpError: If the Google API call fails for a reason other than the
            member already existing (HTTP 409).
    """
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
    """Remove a user from the Google Group used to gate BD Pro access.

    Refuses to remove admin accounts, and refuses to remove any account that
    still has an active subscriber flag or an active non-chatbot
    subscription (chatbot subscriptions don't grant Google Group access, so
    they don't block removal here).

    Args:
        email: Email address to remove; matched against the account's email
            or gcp_email (raw and +alias-normalized).
        group_key: Google Group key to remove the member from. Defaults to
            `settings.GOOGLE_DIRECTORY_GROUP_KEY`.
        event_context: Human-readable context prefixed to log messages.

    Raises:
        HttpError: If the Google API call fails for a reason other than the
            member not being found (HTTP 404/400).
        Exception: Any other unexpected error during removal.
    """
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

        has_active_sub = getattr(
            user, "is_subscriber", False
        ) or _account_has_active_non_chatbot_subscription(user)

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


def apply_active_subscription_entitlements(
    wc: WebhookContext,
    subscription: Subscription | None,
    account: Account | None,
    *,
    chatbot_grant_message: str | None = None,
) -> None:
    """Grant entitlements for an active, trialing, or resumed subscription.

    Routes the grant based on the subscription's product: chatbot
    subscriptions set `account.has_chatbot_access`, other products add the
    customer to the Google Group. If there's no matching internal account
    and the product isn't chatbot, the Google Group is granted by email
    alone.

    Args:
        wc: Context for the originating webhook event.
        subscription: Internal `Subscription` instance, used to resolve the
            product type.
        account: Account to grant entitlements to, if one exists for the
            Stripe customer.
        chatbot_grant_message: Log message to use when granting chatbot
            access. Defaults to a generic "Liberando acesso..." message.
    """
    is_chat = subscription_product_is_chatbot(subscription, wc.event, wc.event_context)
    grant_msg = (
        chatbot_grant_message or f"Liberando acesso ao chatbot para o cliente {wc.customer_email}"
    )
    if account:
        if is_chat:
            _set_account_chatbot_access(account, True, wc, grant_msg)
        else:
            try:
                add_user(
                    account.gcp_email or account.email,
                    account=account,
                    event_context=wc.event_context,
                )
            except Exception as e:
                logger.error(f"{wc.ctx}{e}")
    elif not is_chat:
        try:
            add_user(
                wc.customer_email,
                account=None,
                event_context=wc.event_context,
            )
        except Exception as e:
            logger.error(f"{wc.ctx}{e}")


def apply_inactive_subscription_entitlements(
    wc: WebhookContext,
    subscription: Subscription | None,
    account: Account | None,
    *,
    chatbot_revoke_message: str | None = None,
) -> None:
    """Revoke entitlements for an inactive, deleted, or paused subscription.

    Routes the revocation based on the subscription's product: for chatbot
    subscriptions, access is only revoked if the account has no other
    active/trialing chatbot subscription; for other products, the customer
    is removed from the Google Group.

    Args:
        wc: Context for the originating webhook event.
        subscription: Internal `Subscription` instance, used to resolve the
            product type.
        account: Account to revoke entitlements from, if one exists for the
            Stripe customer.
        chatbot_revoke_message: Log message to use when revoking chatbot
            access. Defaults to a generic "Removendo acesso..." message.
    """
    is_chat = subscription_product_is_chatbot(subscription, wc.event, wc.event_context)
    revoke_msg = (
        chatbot_revoke_message or f"Removendo acesso ao chatbot para o cliente {wc.customer_email}"
    )
    if is_chat and account:
        ev_sub_id = wc.event.data.get("object", {}).get("id")
        if _account_has_other_active_chatbot_subscription(account, ev_sub_id):
            logger.info(
                f"{wc.ctx}Acesso ao chatbot mantido para {wc.customer_email}: "
                f"outra assinatura ativa/trial do chatbot no cliente Stripe "
                f"(evento trata da assinatura {ev_sub_id})."
            )
        else:
            _set_account_chatbot_access(account, False, wc, revoke_msg)
    elif not is_chat:
        try:
            if account:
                remove_user(
                    account.gcp_email or account.email,
                    event_context=wc.event_context,
                )
            else:
                remove_user(wc.customer_email, event_context=wc.event_context)
        except Exception as e:
            logger.error(f"{wc.ctx}{e}")


def list_user(group_key: str = None):
    """List members of a Google Group.

    Args:
        group_key: Google Group key to list. Defaults to
            `settings.GOOGLE_DIRECTORY_GROUP_KEY`.

    Returns:
        The Google Directory API response listing the group's members.

    Raises:
        Exception: If the Google API call fails.
    """
    if not group_key:
        group_key = settings.GOOGLE_DIRECTORY_GROUP_KEY
    try:
        service = get_service()
        return service.members().list(groupKey=group_key).execute()
    except Exception as e:
        logger.error(e)
        raise e


def is_email_in_group(email: str, group_key: str = None) -> bool:
    """Check whether an email address is a member of a Google Group.

    Args:
        email: Email address to check; normalized before lookup.
        group_key: Google Group key to check. Defaults to
            `settings.GOOGLE_DIRECTORY_GROUP_KEY`.

    Returns:
        `True` if the email is a member of the group. `False` if it isn't a
        member or the lookup fails with an HTTP error.

    Raises:
        Exception: If an unexpected (non-HTTP) error occurs during lookup.
    """
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
    """Propagate a Stripe customer's email change to the internal Account.

    Args:
        event: The `customer.updated` Stripe webhook event.
        **kwargs: Unused; accepted for compatibility with the djstripe
            webhook handler signature.
    """
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
    """Sync the internal Subscription and entitlements for a status change.

    Shared by `subscription_updated` and `subscribe`. Updates the internal
    `Subscription.is_active` flag to match the Stripe subscription status,
    then grants or revokes entitlements accordingly:

    - `trialing`/`active`: grants entitlements.
    - `incomplete`: checkout still in progress; only the internal record is
      updated, entitlements are left untouched.
    - any other status: revokes entitlements.

    Args:
        event: The Stripe subscription webhook event to handle.
    """
    wc = require_webhook_customer_context(event, log_if_invalid=True)
    if not wc:
        return

    subscription = get_subscription(event, event_context=wc.event_context)
    account = get_account_for_stripe_customer(event)

    status = event.data.get("object", {}).get("status")

    if status in ["trialing", "active"]:
        if subscription:
            logger.info(f"{wc.ctx}Adicionando a inscrição do cliente {wc.customer_email}")
            subscription.is_active = True
            subscription.save()

        apply_active_subscription_entitlements(wc, subscription, account)
    elif status == "incomplete":
        if subscription:
            logger.info(
                f"{wc.ctx}Assinatura incompleta (checkout em andamento) para "
                f"{wc.customer_email}; atualizando apenas o registro interno."
            )
            subscription.is_active = False
            subscription.save()
        return
    else:
        if subscription:
            logger.info(
                f"{wc.ctx}Removendo a inscrição do cliente {wc.customer_email} "
                f"(Status via Stripe: {status})"
            )
            subscription.is_active = False
            subscription.save()

        apply_inactive_subscription_entitlements(wc, subscription, account)


@webhooks.handler("customer.subscription.updated")
def subscription_updated(event: Event, **kwargs):
    """Handle a Stripe subscription status update.

    Args:
        event: The `customer.subscription.updated` Stripe webhook event.
        **kwargs: Unused; accepted for compatibility with the djstripe
            webhook handler signature.
    """
    handle_subscription(event)


@webhooks.handler("customer.subscription.created")
def subscribe(event: Event, **kwargs):
    """Grant entitlements for a newly created Stripe subscription.

    Args:
        event: The `customer.subscription.created` Stripe webhook event.
        **kwargs: Unused; accepted for compatibility with the djstripe
            webhook handler signature.
    """
    handle_subscription(event)


@webhooks.handler("customer.subscription.deleted")
def unsubscribe(event: Event, **kwargs):
    """Revoke entitlements for a deleted Stripe subscription.

    Args:
        event: The `customer.subscription.deleted` Stripe webhook event.
        **kwargs: Unused; accepted for compatibility with the djstripe
            webhook handler signature.
    """
    wc = require_webhook_customer_context(event, log_if_invalid=False)
    if not wc:
        return

    subscription = get_subscription(event, event_context=wc.event_context)
    if subscription:
        logger.info(f"{wc.ctx}Removendo a inscrição do cliente {wc.customer_email}")
        subscription.is_active = False
        subscription.save()

    account = get_account_for_stripe_customer(event)
    apply_inactive_subscription_entitlements(wc, subscription, account)


@webhooks.handler("customer.subscription.paused")
def pause_subscription(event: Event, **kwargs):
    """Revoke entitlements for a paused Stripe subscription.

    Args:
        event: The `customer.subscription.paused` Stripe webhook event.
        **kwargs: Unused; accepted for compatibility with the djstripe
            webhook handler signature.
    """
    wc = require_webhook_customer_context(event, log_if_invalid=False)
    if not wc:
        return

    account = get_account_for_stripe_customer(event)

    subscription = get_subscription(event, event_context=wc.event_context)
    if subscription:
        logger.info(f"{wc.ctx}Pausando a inscrição do cliente {wc.customer_email}")
        subscription.is_active = False
        subscription.save()

    apply_inactive_subscription_entitlements(
        wc,
        subscription,
        account,
        chatbot_revoke_message=(
            f"Removendo acesso ao chatbot para o cliente {wc.customer_email} (Pausado)"
        ),
    )


@webhooks.handler("customer.subscription.resumed")
def resume_subscription(event: Event, **kwargs):
    """Grant entitlements for a resumed Stripe subscription.

    Args:
        event: The `customer.subscription.resumed` Stripe webhook event.
        **kwargs: Unused; accepted for compatibility with the djstripe
            webhook handler signature.
    """
    wc = require_webhook_customer_context(event, log_if_invalid=False)
    if not wc:
        return

    account = get_account_for_stripe_customer(event)

    subscription = get_subscription(event, event_context=wc.event_context)
    if subscription:
        logger.info(f"{wc.ctx}Resumindo a inscrição do cliente {wc.customer_email}")
        subscription.is_active = True
        subscription.save()

    apply_active_subscription_entitlements(
        wc,
        subscription,
        account,
        chatbot_grant_message=(
            f"Liberando acesso ao chatbot para o cliente {wc.customer_email} (Resumido)"
        ),
    )


@webhooks.handler("setup_intent.succeeded")
def setup_intent_succeeded(event: Event, **kwargs):
    """Finish checkout: save the payment method and start the subscription.

    Triggered after a customer confirms a SetupIntent during checkout. Sets
    the confirmed payment method as the customer's default, then creates a
    trialing subscription for the price encoded in the SetupIntent's
    metadata — unless the customer already has an active/trialing
    subscription of the same product type (chatbot or bd_pro), in which
    case no new subscription is created.

    Ignores SetupIntents whose `backend_url` metadata doesn't match this
    backend's URL (e.g. events from another environment sharing the same
    Stripe account).

    Args:
        event: The `setup_intent.succeeded` Stripe webhook event.
        **kwargs: Unused; accepted for compatibility with the djstripe
            webhook handler signature.
    """
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

    if not price_id:
        return

    is_chatbot_price = _price_is_chatbot(price_id)
    if is_chatbot_price is None:
        logger.warning(f"{ctx}Price {price_id!r} não encontrado; assinatura não criada.")
        return

    if _customer_has_active_subscription_of_type(customer, is_chatbot_price):
        product_label = "chatbot" if is_chatbot_price else "bd_pro"
        return logger.info(
            f"{ctx}Cliente {event.customer.email} já possui assinatura ativa/trial "
            f"do tipo {product_label}; assinatura não criada."
        )

    if promotion_code:
        discounts = [{"promotion_code": promotion_code}]
    else:
        discounts = []

    account = getattr(customer, "subscriber", None) or get_account_for_stripe_customer(event)
    subscribe_kwargs = {"price": price_id, "discounts": discounts}

    skip_trial = False
    if is_chatbot_price:
        skip_trial = bool(account and not account_eligible_for_chatbot_stripe_trial(account))
    else:
        skip_trial = bool(account and not account_eligible_for_bdpro_stripe_trial(account))

    if not skip_trial:
        subscribe_kwargs["trial_period_days"] = 7

    if skip_trial:
        product_label = "chatbot" if is_chatbot_price else "bd_pro"
        logger.info(
            f"{ctx}Cliente {event.customer.email} não elegível a trial do {product_label}; "
            "assinatura criada sem período de trial."
        )
    else:
        logger.info(f"{ctx}Add subscription to user {event.customer.email}")

    customer.subscribe(**subscribe_kwargs)


# Reference
# https://developers.google.com/admin-sdk/directory/v1/guides/troubleshoot-error-codes
# https://developers.google.com/admin-sdk/reseller/v1/support/directory_api_common_errors
