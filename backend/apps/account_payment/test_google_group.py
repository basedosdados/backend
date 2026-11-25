# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from backend.apps.account.models import Account
from backend.apps.account_payment import google_group, webhooks


def _http_error(status: int) -> HttpError:
    resp = MagicMock()
    resp.status = status
    return HttpError(resp, b"")


def _wc():
    return webhooks.WebhookContext(
        event=MagicMock(),
        event_context="Webhook: test | Event ID: evt_1",
        ctx="[Webhook: test | Event ID: evt_1] ",
        customer_email="cliente@email.com",
    )


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def account():
    return Account.objects.create(
        is_active=True,
        password="12345678",
        email="Cliente@Email.com",
        gcp_email="cliente.gcp@gmail.com",
    )


class TestGetAccountForStripeCustomer:
    def test_prefers_djstripe_subscriber(self):
        linked = MagicMock()
        event = MagicMock()
        event.customer.subscriber = linked
        assert webhooks.get_account_for_stripe_customer(event) is linked

    @pytest.mark.django_db
    def test_falls_back_to_case_insensitive_email(self, account):
        event = MagicMock()
        event.customer.subscriber = None
        event.customer.email = "cliente@email.com "
        assert webhooks.get_account_for_stripe_customer(event) == account


class TestRetryableGoogleError:
    @pytest.mark.parametrize("status", [401, 403, 429, 500, 503])
    def test_retryable_statuses(self, status):
        assert webhooks.is_retryable_google_error(_http_error(status))

    @pytest.mark.parametrize("status", [400, 404])
    def test_permanent_statuses(self, status):
        assert not webhooks.is_retryable_google_error(_http_error(status))

    def test_non_http_errors_are_retryable(self):
        assert webhooks.is_retryable_google_error(RefreshError("invalid_grant"))


class TestAddUser:
    @patch.object(webhooks, "is_stg", return_value=False)
    @patch.object(webhooks, "is_dev", return_value=False)
    @patch.object(webhooks, "send")
    @patch.object(webhooks, "get_service")
    def test_invalid_credentials_alert_and_raise(self, get_service, send, *_):
        get_service.return_value.members.return_value.insert.return_value.execute.side_effect = (
            RefreshError("invalid_grant")
        )
        with pytest.raises(RefreshError):
            webhooks.add_user("cliente@email.com")
        send.assert_called_once()
        assert "Credencial do Google Groups inválida" in send.call_args.args[0]

    @patch.object(webhooks, "is_stg", return_value=False)
    @patch.object(webhooks, "is_dev", return_value=False)
    @patch.object(webhooks, "send")
    @patch.object(webhooks, "get_service")
    def test_already_member_is_not_an_error(self, get_service, send, *_):
        get_service.return_value.members.return_value.insert.return_value.execute.side_effect = (
            _http_error(409)
        )
        webhooks.add_user("cliente@email.com")
        send.assert_not_called()


class TestRemoveUser:
    @patch.object(webhooks, "is_stg", return_value=True)
    @patch.object(webhooks, "is_dev", return_value=False)
    @patch.object(webhooks, "get_service")
    def test_skipped_in_staging(self, get_service, *_):
        webhooks.remove_user("cliente@email.com")
        get_service.assert_not_called()

    @patch.object(webhooks, "is_stg", return_value=False)
    @patch.object(webhooks, "is_dev", return_value=True)
    @patch.object(webhooks, "get_service")
    def test_skipped_in_dev(self, get_service, *_):
        webhooks.remove_user("cliente@email.com")
        get_service.assert_not_called()

    @pytest.mark.django_db
    @patch.object(webhooks, "is_stg", return_value=False)
    @patch.object(webhooks, "is_dev", return_value=False)
    @patch.object(webhooks, "get_service")
    def test_removes_in_production(self, get_service, *_):
        webhooks.remove_user("Cliente+x@email.com")
        get_service.return_value.members.return_value.delete.assert_called_once_with(
            groupKey=webhooks.settings.GOOGLE_DIRECTORY_GROUP_KEY,
            memberKey="cliente@email.com",
        )


class TestCredentialsAlert:
    @patch.object(webhooks, "send")
    def test_alerts_once_per_interval(self, send):
        for _ in range(3):
            webhooks.alert_google_credentials(RefreshError("invalid_grant"))
        send.assert_called_once()

    @patch.object(webhooks, "send")
    def test_alerts_again_after_interval(self, send):
        webhooks.alert_google_credentials(RefreshError("invalid_grant"))
        cache.delete(webhooks.GOOGLE_CREDENTIALS_ALERT_KEY)
        webhooks.alert_google_credentials(RefreshError("invalid_grant"))
        assert send.call_count == 2


class TestEntitlementFailures:
    @patch.object(webhooks, "subscription_product_is_chatbot", return_value=False)
    @patch.object(webhooks, "add_user", side_effect=_http_error(403))
    def test_retryable_failure_raises_so_stripe_retries(self, *_):
        account = MagicMock(gcp_email="", email="cliente@email.com")
        with pytest.raises(HttpError):
            webhooks.apply_active_subscription_entitlements(_wc(), MagicMock(), account)

    @patch.object(webhooks, "subscription_product_is_chatbot", return_value=False)
    @patch.object(webhooks, "add_user", side_effect=_http_error(400))
    def test_permanent_failure_is_only_logged(self, *_):
        account = MagicMock(gcp_email="", email="cliente@email.com")
        webhooks.apply_active_subscription_entitlements(_wc(), MagicMock(), account)

    @patch.object(webhooks, "subscription_product_is_chatbot", return_value=False)
    @patch.object(webhooks, "remove_user", side_effect=RefreshError("invalid_grant"))
    def test_remove_failure_raises(self, *_):
        account = MagicMock(gcp_email="", email="cliente@email.com")
        with pytest.raises(RefreshError):
            webhooks.apply_inactive_subscription_entitlements(_wc(), MagicMock(), account)


class TestStripeEventContext:
    def test_handler_logs_carry_event_fields(self):
        captured = []
        handler_id = webhooks.logger.add(lambda m: captured.append(m.record["extra"]))
        try:

            @webhooks.with_stripe_event_context
            def handler(event, **kwargs):
                webhooks.logger.info("dentro do handler")

            event = MagicMock(id="evt_1", type="customer.subscription.updated")
            event.data = {"object": {"id": "sub_1", "status": "active"}}
            event.customer.id = "cus_1"
            event.customer.email = "cliente@email.com"
            handler(event)
        finally:
            webhooks.logger.remove(handler_id)

        assert captured[-1]["stripe_event_id"] == "evt_1"
        assert captured[-1]["stripe_object_id"] == "sub_1"
        assert captured[-1]["stripe_customer_id"] == "cus_1"


def _subscription(admin, stripe_id=None, status="active", subscribers=(), is_active=True):
    sub = MagicMock()
    sub.id = f"sub-{admin.email}"
    sub.admin = admin
    sub.is_active = is_active
    sub.subscription.id = stripe_id or f"stripe-{admin.email}"
    sub.subscription.status = status
    sub.subscribers.all.return_value = list(subscribers)
    return sub


def _paid(subscription, status="active"):
    return google_group.PaidStripeSubscription(
        id=subscription.subscription.id, customer_id="cus_1", status=status
    )


@pytest.mark.django_db
class TestAuditGoogleGroup:
    def _account(self, email, gcp_email=None, is_admin=False):
        return Account.objects.create(
            email=email, gcp_email=gcp_email, is_admin=is_admin, password="12345678"
        )

    def _audit(self, group, paid=(), internal=(), active=(), customer=(None, "cus_1")):
        with (
            patch.object(google_group, "list_group_members", return_value=set(group)),
            patch.object(google_group, "paid_pro_subscriptions_in_stripe", return_value=list(paid)),
            patch.object(
                google_group,
                "internal_subscriptions",
                return_value={s.subscription.id: s for s in internal},
            ),
            patch.object(google_group, "active_pro_subscriptions", return_value=list(active)),
            patch.object(google_group, "customer_account", return_value=customer),
            patch.object(google_group, "stripe_status", side_effect=lambda s: "canceled"),
        ):
            return google_group.audit_google_group()

    def test_finds_missing_stale_and_extra(self):
        owner = self._account("dono@email.com", gcp_email="dono+bq@gmail.com")
        member = self._account("membro@email.com")
        stale_owner = self._account("antigo@email.com")
        admin = self._account("admin@email.com", is_admin=True)

        paid_sub = _subscription(owner, subscribers=[member])
        stale_sub = _subscription(stale_owner)
        group = {"dono@gmail.com", "antigo@email.com", "sobrando@email.com", admin.email}

        audit = self._audit(
            group, paid=[_paid(paid_sub)], internal=[paid_sub], active=[paid_sub, stale_sub]
        )

        assert [email for email, _, _ in audit.missing] == ["membro@email.com"]
        assert audit.stale == [("antigo@email.com", "sub-antigo@email.com", "canceled")]
        assert audit.extra == ["antigo@email.com", "sobrando@email.com"]
        assert audit.inactive == []
        assert audit.unlinked == []
        assert not audit.ok

    def test_stale_subscription_out_of_group_is_not_missing(self):
        """Canceled in Stripe but still `is_active` in the database: never added back."""
        owner = self._account("cancelado@email.com")
        member = self._account("membro.cancelado@email.com")
        stale_sub = _subscription(owner, subscribers=[member])

        audit = self._audit(set(), active=[stale_sub])

        assert audit.missing == []
        assert audit.expected == set()
        assert [email for email, _, _ in audit.stale] == ["cancelado@email.com"]

    def test_canceled_at_period_end_stays_expected(self):
        """Annual plan canceled in the first month: Stripe keeps `active` until period end."""
        owner = self._account("anual@email.com")
        subscription = _subscription(owner)
        subscription.subscription.cancel_at_period_end = True

        audit = self._audit(
            set(), paid=[_paid(subscription)], internal=[subscription], active=[subscription]
        )

        assert [email for email, _, _ in audit.missing] == ["anual@email.com"]
        assert audit.stale == []

    def test_paid_in_stripe_but_inactive_in_database(self):
        """Webhook failed until Stripe gave up: is_active=False, but the customer paid."""
        owner = self._account("pagou@email.com")
        subscription = _subscription(owner, is_active=False)

        audit = self._audit(set(), paid=[_paid(subscription)], internal=[subscription])

        assert audit.inactive == [("pagou@email.com", "sub-pagou@email.com", "active")]
        assert [email for email, _, _ in audit.missing] == ["pagou@email.com"]
        assert not audit.ok

    def test_paid_in_stripe_without_internal_subscription(self):
        owner = self._account("sem.registro@email.com")
        paid = google_group.PaidStripeSubscription("sub_stripe", "cus_9", "trialing")

        audit = self._audit(set(), paid=[paid], customer=(owner, "sem.registro@email.com"))

        assert audit.unlinked == [("sem.registro@email.com", "sub_stripe")]
        assert audit.missing == [("sem.registro@email.com", owner.id, "sub_stripe")]

    def test_paid_without_account_is_only_reported(self):
        paid = google_group.PaidStripeSubscription("sub_stripe", "cus_9", "active")

        audit = self._audit(set(), paid=[paid], customer=(None, "cus_9"))

        assert audit.unlinked == [("cus_9", "sub_stripe")]
        assert audit.missing == []

    def test_everything_in_sync_is_ok(self):
        owner = self._account("ok@email.com")
        subscription = _subscription(owner)

        audit = self._audit(
            {"ok@email.com"},
            paid=[_paid(subscription)],
            internal=[subscription],
            active=[subscription],
        )

        assert audit.ok
        assert audit.extra == []


class TestPaidProSubscriptionsInStripe:
    def _stripe_sub(self, sub_id, product, customer="cus_1"):
        return {
            "id": sub_id,
            "customer": customer,
            "items": {"data": [{"price": {"product": product}}]},
        }

    @pytest.mark.django_db
    def test_lists_only_bd_pro_in_both_statuses(self):
        by_status = {
            "active": [
                self._stripe_sub("sub_pro", "prod_pro"),
                self._stripe_sub("sub_chatbot", "prod_chatbot"),
            ],
            "trialing": [self._stripe_sub("sub_empresas", {"id": "prod_empresas"})],
        }
        codes = {
            "prod_pro": "bd_pro",
            "prod_chatbot": "chatbot",
            "prod_empresas": "bd_pro_empresas",
        }

        def list_subscriptions(status, **_):
            result = MagicMock()
            result.auto_paging_iter.return_value = iter(by_status[status])
            return result

        with (
            patch.object(google_group.stripe.Subscription, "list", side_effect=list_subscriptions),
            patch.object(
                google_group.stripe.Product,
                "retrieve",
                side_effect=lambda product_id, **_: {"metadata": {"code": codes[product_id]}},
            ) as retrieve,
        ):
            paid = google_group.paid_pro_subscriptions_in_stripe()

        assert paid == [
            google_group.PaidStripeSubscription("sub_pro", "cus_1", "active"),
            google_group.PaidStripeSubscription("sub_empresas", "cus_1", "trialing"),
        ]
        assert retrieve.call_count == 3

    def test_list_group_members_follows_pagination(self):
        service = MagicMock()
        service.members.return_value.list.return_value.execute.side_effect = [
            {"members": [{"email": "A@email.com"}], "nextPageToken": "p2"},
            {"members": [{"email": "b+x@email.com"}]},
        ]
        with patch.object(google_group, "get_service", return_value=service):
            assert google_group.list_group_members("grupo") == {"a@email.com", "b@email.com"}


@pytest.mark.django_db
class TestDatabaseLookups:
    def test_internal_subscriptions_query_is_valid(self):
        assert google_group.internal_subscriptions({"sub_inexistente"}) == {}

    def test_customer_account_falls_back_to_stripe_email(self, account):
        with patch.object(
            google_group.stripe.Customer,
            "retrieve",
            return_value={"email": " CLIENTE@email.com "},
        ):
            assert google_group.customer_account("cus_sem_local") == (account, "CLIENTE@email.com")

    def test_customer_account_without_email_uses_customer_id(self):
        with patch.object(google_group.stripe.Customer, "retrieve", return_value={"email": None}):
            assert google_group.customer_account("cus_9") == (None, "cus_9")

    def test_stripe_status_falls_back_to_local_status(self):
        subscription = MagicMock()
        subscription.subscription.status = "active"
        with patch.object(
            google_group.stripe.Subscription,
            "retrieve",
            side_effect=google_group.stripe.error.APIConnectionError("offline"),
        ):
            assert google_group.stripe_status(subscription) == "active"
