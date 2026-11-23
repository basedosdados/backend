# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest
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


def _subscription(admin, status="active", subscribers=()):
    sub = MagicMock()
    sub.id = f"sub-{admin.email}"
    sub.admin = admin
    sub.subscription.status = status
    sub.subscribers.all.return_value = list(subscribers)
    return sub


@pytest.mark.django_db
class TestAuditGoogleGroup:
    def _account(self, email, gcp_email=None, is_admin=False):
        return Account.objects.create(
            email=email, gcp_email=gcp_email, is_admin=is_admin, password="12345678"
        )

    def test_finds_missing_stale_and_extra(self):
        owner = self._account("dono@email.com", gcp_email="dono+bq@gmail.com")
        member = self._account("membro@email.com")
        stale_owner = self._account("antigo@email.com")
        admin = self._account("admin@email.com", is_admin=True)

        subscriptions = [
            _subscription(owner, subscribers=[member]),
            _subscription(stale_owner, status="canceled"),
        ]
        group = {"dono@gmail.com", "antigo@email.com", "sobrando@email.com", admin.email}

        with (
            patch.object(google_group, "list_group_members", return_value=group),
            patch.object(google_group, "active_pro_subscriptions", return_value=subscriptions),
        ):
            audit = google_group.audit_google_group()

        assert [email for email, _, _ in audit.missing] == ["membro@email.com"]
        assert audit.stale == [("antigo@email.com", "sub-antigo@email.com", "canceled")]
        assert audit.extra == ["sobrando@email.com"]
        assert not audit.ok

    def test_list_group_members_follows_pagination(self):
        service = MagicMock()
        service.members.return_value.list.return_value.execute.side_effect = [
            {"members": [{"email": "A@email.com"}], "nextPageToken": "p2"},
            {"members": [{"email": "b+x@email.com"}]},
        ]
        with patch.object(google_group, "get_service", return_value=service):
            assert google_group.list_group_members("grupo") == {"a@email.com", "b@email.com"}
