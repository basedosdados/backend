# -*- coding: utf-8 -*-
"""Tests for the admin_data_tools endpoints."""

import json
from unittest.mock import patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from backend.apps.api.v1.models import CloudTable, Dataset, Table

from .admin import DisabledFlowScheduleAdmin, activate_selected, deactivate_selected
from .models import DisabledFlowSchedule

TOKEN = "test-token"
AUTH = {"HTTP_AUTHORIZATION": f"Bearer {TOKEN}"}


@override_settings(ALLOWED_HOSTS=["testserver"])
class SyncDeploymentsViewTests(TestCase):
    """Cover the schedule-filtering behavior of the sync endpoint.

    A deployment with no Prefect schedule attached (e.g. a stage only ever
    triggered via ``run_deployment()`` from another flow, never on a cron) is
    not an arming candidate — there is nothing to pause or unpause — so it
    must never show up in ``DisabledFlowSchedule``.
    """

    def setUp(self):
        self.client = Client()
        self.url = reverse("sync-deployments")

    def _post(self):
        return self.client.post(self.url, **AUTH)

    def _mock_deployments(self, mock_client, deployments):
        mock_client.return_value.iter_deployments.return_value = iter(deployments)

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    @patch("backend.apps.admin_data_tools.flow_monitoring.Prefect3Client")
    def test_unscheduled_deployment_is_skipped_not_created(self, mock_client):
        self._mock_deployments(
            mock_client,
            [{"id": "d1", "name": "extract_and_load: foo", "paused": True, "schedules": []}],
        )
        resp = self._post()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["created"], 0)
        self.assertFalse(
            DisabledFlowSchedule.objects.filter(flow_name="extract_and_load: foo").exists()
        )
        mock_client.return_value.set_paused.assert_not_called()

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    @patch("backend.apps.admin_data_tools.flow_monitoring.Prefect3Client")
    def test_existing_record_removed_when_schedule_is_gone(self, mock_client):
        DisabledFlowSchedule.objects.create(
            flow_name="build_and_promote: foo", deployment_id="d2", is_schedule_active=True
        )
        self._mock_deployments(
            mock_client,
            [{"id": "d2", "name": "build_and_promote: foo", "paused": False, "schedules": []}],
        )
        resp = self._post()
        self.assertEqual(resp.json()["removed_no_schedule"], 1)
        self.assertFalse(
            DisabledFlowSchedule.objects.filter(flow_name="build_and_promote: foo").exists()
        )
        mock_client.return_value.set_paused.assert_not_called()

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    @patch("backend.apps.admin_data_tools.flow_monitoring.Prefect3Client")
    def test_scheduled_unknown_deployment_is_still_created(self, mock_client):
        self._mock_deployments(
            mock_client,
            [
                {
                    "id": "d3",
                    "name": "check_update: foo",
                    "paused": True,
                    "schedules": [{"id": "s1"}],
                }
            ],
        )
        resp = self._post()
        self.assertEqual(resp.json()["created"], 1)
        record = DisabledFlowSchedule.objects.get(flow_name="check_update: foo")
        self.assertFalse(record.is_schedule_active)

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    @patch("backend.apps.admin_data_tools.flow_monitoring.Prefect3Client")
    def test_scheduled_known_deployment_enforces_stored_state(self, mock_client):
        DisabledFlowSchedule.objects.create(
            flow_name="check_update: bar", deployment_id="d4", is_schedule_active=True
        )
        self._mock_deployments(
            mock_client,
            [
                {
                    "id": "d4",
                    "name": "check_update: bar",
                    "paused": True,
                    "schedules": [{"id": "s1"}],
                }
            ],
        )
        resp = self._post()
        self.assertEqual(resp.json()["activated"], 1)
        mock_client.return_value.set_paused.assert_called_once_with("d4", paused=False)


@override_settings(ALLOWED_HOSTS=["testserver"])
class SyncDeploymentsTableLinkTests(TestCase):
    """Cover resolving which `Table`(s) a deployment feeds.

    Tried in order: the deployment's own `"<dataset_id>__<table_id>"` tag
    (`deploy_tags()`, pipelines repo — flows already migrated) or the
    deployment NAME itself (pre-migration monolithic flows long since named
    that way); falling that, when there's no double underscore anywhere, the
    name minus a `"_flow"` suffix treated as a bare dataset_id, resolving to
    every table under it — covers a monolithic flow feeding several tables
    from one deployment (confirmed for real: `br_me_siconfi_flow`, 7
    tables). None of these resolving is the normal case, never an error.
    """

    def setUp(self):
        self.client = Client()
        self.url = reverse("sync-deployments")
        self.dataset = Dataset.objects.create(slug="br_ans_beneficiario", name="ANS")
        self.table = Table.objects.create(
            dataset=self.dataset, slug="informacao_consolidada", name="Informação consolidada"
        )
        CloudTable.objects.create(
            table=self.table,
            gcp_project_id="basedosdados",
            gcp_dataset_id="br_ans_beneficiario",
            gcp_table_id="informacao_consolidada",
        )

    def _post(self):
        return self.client.post(self.url, **AUTH)

    def _mock_deployments(self, mock_client, deployments):
        mock_client.return_value.iter_deployments.return_value = iter(deployments)

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    @patch("backend.apps.admin_data_tools.flow_monitoring.Prefect3Client")
    def test_new_deployment_links_table_from_tag(self, mock_client):
        self._mock_deployments(
            mock_client,
            [
                {
                    "id": "d1",
                    "name": "check_update: br_ans_beneficiario__informacao_consolidada",
                    "paused": True,
                    "schedules": [{"id": "s1"}],
                    "tags": [
                        "staged-pipeline",
                        "check_update",
                        "br_ans_beneficiario",
                        "br_ans_beneficiario__informacao_consolidada",
                    ],
                }
            ],
        )
        resp = self._post()
        self.assertEqual(resp.json()["tables_linked"], 1)
        self.table.refresh_from_db()
        record = DisabledFlowSchedule.objects.get(
            flow_name="check_update: br_ans_beneficiario__informacao_consolidada"
        )
        self.assertEqual(self.table.flow_schedule_id, record.id)
        self.assertTrue(self.table.has_flow_schedule)

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    @patch("backend.apps.admin_data_tools.flow_monitoring.Prefect3Client")
    def test_legacy_deployment_links_table_from_its_own_name(self, mock_client):
        """Pre-migration monolithic flows carry none of the new tags, but
        are long since named "<dataset_id>__<table_id>" directly."""
        self._mock_deployments(
            mock_client,
            [
                {
                    "id": "d2",
                    "name": "br_ans_beneficiario__informacao_consolidada",
                    "paused": True,
                    "schedules": [{"id": "s1"}],
                    "tags": ["automated-deploy", "env:prod"],
                }
            ],
        )
        self._post()
        self.table.refresh_from_db()
        record = DisabledFlowSchedule.objects.get(
            flow_name="br_ans_beneficiario__informacao_consolidada"
        )
        self.assertEqual(self.table.flow_schedule_id, record.id)

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    @patch("backend.apps.admin_data_tools.flow_monitoring.Prefect3Client")
    def test_no_matching_signal_leaves_table_unlinked_without_error(self, mock_client):
        self._mock_deployments(
            mock_client,
            [
                {
                    "id": "d3",
                    "name": "br_old_monolithic_flow",
                    "paused": True,
                    "schedules": [{"id": "s1"}],
                    "tags": ["automated-deploy", "dataset:br_old_monolithic_flow"],
                }
            ],
        )
        resp = self._post()
        self.assertEqual(resp.json()["errors"], 0)
        self.assertEqual(resp.json()["tables_linked"], 0)

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    @patch("backend.apps.admin_data_tools.flow_monitoring.Prefect3Client")
    def test_monolithic_flow_links_every_table_under_its_dataset(self, mock_client):
        """A single deployment feeding several tables at once (e.g. the
        real-world `br_me_siconfi_flow`, 7 tables) — no tag, no "__"
        anywhere, just the bare dataset_id plus a "_flow" suffix."""
        other_table = Table.objects.create(
            dataset=self.dataset, slug="outra_tabela", name="Outra Tabela"
        )
        CloudTable.objects.create(
            table=other_table,
            gcp_project_id="basedosdados",
            gcp_dataset_id="br_ans_beneficiario",
            gcp_table_id="outra_tabela",
        )
        self._mock_deployments(
            mock_client,
            [
                {
                    "id": "d4",
                    "name": "br_ans_beneficiario_flow",
                    "paused": True,
                    "schedules": [{"id": "s1"}],
                    "tags": ["automated-deploy", "env:prod"],
                }
            ],
        )
        resp = self._post()
        self.assertEqual(resp.json()["tables_linked"], 2)
        record = DisabledFlowSchedule.objects.get(flow_name="br_ans_beneficiario_flow")
        self.assertCountEqual(
            record.tables.values_list("id", flat=True), [self.table.id, other_table.id]
        )

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    @patch("backend.apps.admin_data_tools.flow_monitoring.Prefect3Client")
    def test_monolithic_fallback_never_claims_a_table_with_its_own_dedicated_flow(
        self, mock_client
    ):
        """Real scenario: a dataset where every table but one comes from the
        same monolithic flow — that one table has its own dedicated
        deployment instead. The whole-dataset fallback must skip it, no
        matter which deployment Prefect happens to list first."""
        dedicated_table = Table.objects.create(
            dataset=self.dataset, slug="tabela_dedicada", name="Tabela Dedicada"
        )
        CloudTable.objects.create(
            table=dedicated_table,
            gcp_project_id="basedosdados",
            gcp_dataset_id="br_ans_beneficiario",
            gcp_table_id="tabela_dedicada",
        )
        self._mock_deployments(
            mock_client,
            [
                {
                    "id": "d5",
                    "name": "br_ans_beneficiario_flow",
                    "paused": True,
                    "schedules": [{"id": "s1"}],
                    "tags": ["automated-deploy", "env:prod"],
                },
                {
                    "id": "d6",
                    "name": "check_update: br_ans_beneficiario__tabela_dedicada",
                    "paused": True,
                    "schedules": [{"id": "s2"}],
                    "tags": ["staged-pipeline", "br_ans_beneficiario__tabela_dedicada"],
                },
            ],
        )
        self._post()

        monolithic = DisabledFlowSchedule.objects.get(flow_name="br_ans_beneficiario_flow")
        dedicated = DisabledFlowSchedule.objects.get(
            flow_name="check_update: br_ans_beneficiario__tabela_dedicada"
        )
        self.assertCountEqual(monolithic.tables.values_list("id", flat=True), [self.table.id])
        dedicated_table.refresh_from_db()
        self.assertEqual(dedicated_table.flow_schedule_id, dedicated.id)


@override_settings(ALLOWED_HOSTS=["testserver"])
class SetScheduleActiveViewTests(TestCase):
    """Cover the programmatic arming endpoint.

    The endpoint must do the same three things as the admin form — update the
    stored state, stamp ``reactivated_at`` and pause/unpause Prefect — because
    flipping only Prefect is undone by the next sync.
    """

    def setUp(self):
        self.client = Client()
        self.url = reverse("set-schedule-active")
        self.record = DisabledFlowSchedule.objects.create(
            flow_name="au_rba_statistical_tables/au_rba_statistical_tables_flow",
            deployment_id="628338b2-0f2b-472f-b629-544028134913",
            is_schedule_active=False,
        )

    def _post(self, payload, **extra):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type="application/json", **extra
        )

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    @patch("backend.apps.admin_data_tools.schedule_actions.Prefect3Client")
    def test_arming_updates_db_and_unpauses_prefect(self, mock_client):
        resp = self._post({"flow_name": self.record.flow_name, "is_schedule_active": True}, **AUTH)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["action"], "activated")
        self.assertTrue(body["is_schedule_active"])
        self.assertIsNotNone(body["reactivated_at"])

        mock_client.return_value.set_paused.assert_called_once_with(
            self.record.deployment_id, paused=False
        )

        self.record.refresh_from_db()
        self.assertTrue(self.record.is_schedule_active)
        self.assertIsNotNone(self.record.reactivated_at)

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    @patch("backend.apps.admin_data_tools.schedule_actions.Prefect3Client")
    def test_disarming_clears_reactivated_at_and_pauses_prefect(self, mock_client):
        self.record.is_schedule_active = True
        self.record.save()

        resp = self._post({"flow_name": self.record.flow_name, "is_schedule_active": False}, **AUTH)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["action"], "disabled")

        mock_client.return_value.set_paused.assert_called_once_with(
            self.record.deployment_id, paused=True
        )

        self.record.refresh_from_db()
        self.assertFalse(self.record.is_schedule_active)
        self.assertIsNone(self.record.reactivated_at)

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    @patch("backend.apps.admin_data_tools.schedule_actions.Prefect3Client")
    def test_setting_current_state_is_a_safe_noop(self, mock_client):
        """Doubles as the auth smoke test: reaches the view, touches nothing."""
        resp = self._post({"flow_name": self.record.flow_name, "is_schedule_active": False}, **AUTH)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["action"], "no_change")
        mock_client.return_value.set_paused.assert_not_called()

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    @patch("backend.apps.admin_data_tools.schedule_actions.Prefect3Client")
    def test_prefect_failure_leaves_stored_state_untouched(self, mock_client):
        """Prefect is called first, so a failure must not claim a change."""
        mock_client.return_value.set_paused.side_effect = RuntimeError("prefect down")

        with self.assertRaises(RuntimeError):
            self._post({"flow_name": self.record.flow_name, "is_schedule_active": True}, **AUTH)

        self.record.refresh_from_db()
        self.assertFalse(self.record.is_schedule_active)
        self.assertIsNone(self.record.reactivated_at)

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    def test_unknown_flow_returns_404(self):
        resp = self._post({"flow_name": "nope/nope", "is_schedule_active": True}, **AUTH)
        self.assertEqual(resp.status_code, 404)
        self.assertIn("sync-deployments", resp.json()["error"])

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    def test_bad_payload_returns_400(self):
        for payload in (
            {"flow_name": self.record.flow_name},  # missing bool
            {"is_schedule_active": True},  # missing name
            {"flow_name": self.record.flow_name, "is_schedule_active": "yes"},  # not a bool
        ):
            resp = self._post(payload, **AUTH)
            self.assertEqual(resp.status_code, 400, payload)

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    def test_invalid_json_returns_400(self):
        resp = self.client.post(self.url, data="not json", content_type="application/json", **AUTH)
        self.assertEqual(resp.status_code, 400)

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    @patch("backend.apps.admin_data_tools.schedule_actions.Prefect3Client")
    def test_bad_token_is_rejected_before_any_write(self, mock_client):
        resp = self._post(
            {"flow_name": self.record.flow_name, "is_schedule_active": True},
            HTTP_AUTHORIZATION="Bearer wrong",
        )
        self.assertEqual(resp.status_code, 401)
        mock_client.return_value.set_paused.assert_not_called()
        self.record.refresh_from_db()
        self.assertFalse(self.record.is_schedule_active)


class DisabledFlowScheduleAdminActionsTests(TestCase):
    """Cover the admin's bulk actions and the list_editable checkbox path.

    Both go through `apply_schedule_state` (already covered against Prefect
    failure/no-op in `SetScheduleActiveViewTests`) — these tests focus on
    what's specific to the admin: only touching rows that actually need to
    change, and reporting a summary instead of raising on a partial failure.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.active = DisabledFlowSchedule.objects.create(
            flow_name="already_active_flow", deployment_id="d1", is_schedule_active=True
        )
        self.inactive = DisabledFlowSchedule.objects.create(
            flow_name="already_inactive_flow", deployment_id="d2", is_schedule_active=False
        )

    def _request(self):
        request = self.factory.post("/admin/admin_data_tools/disabledflowschedule/")
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    @patch("backend.apps.admin_data_tools.schedule_actions.Prefect3Client")
    def test_activate_selected_only_arms_inactive_rows(self, mock_client):
        queryset = DisabledFlowSchedule.objects.filter(pk__in=[self.active.pk, self.inactive.pk])
        activate_selected(None, self._request(), queryset)

        mock_client.return_value.set_paused.assert_called_once_with("d2", paused=False)
        self.inactive.refresh_from_db()
        self.assertTrue(self.inactive.is_schedule_active)
        self.assertIsNotNone(self.inactive.reactivated_at)

    @patch("backend.apps.admin_data_tools.schedule_actions.Prefect3Client")
    def test_deactivate_selected_only_disarms_active_rows(self, mock_client):
        queryset = DisabledFlowSchedule.objects.filter(pk__in=[self.active.pk, self.inactive.pk])
        deactivate_selected(None, self._request(), queryset)

        mock_client.return_value.set_paused.assert_called_once_with("d1", paused=True)
        self.active.refresh_from_db()
        self.assertFalse(self.active.is_schedule_active)
        self.assertIsNone(self.active.reactivated_at)

    @patch("backend.apps.admin_data_tools.schedule_actions.Prefect3Client")
    def test_one_failure_does_not_abort_the_rest_of_the_batch(self, mock_client):
        other_inactive = DisabledFlowSchedule.objects.create(
            flow_name="another_inactive_flow", deployment_id="d3", is_schedule_active=False
        )
        mock_client.return_value.set_paused.side_effect = [RuntimeError("prefect down"), None]

        queryset = DisabledFlowSchedule.objects.filter(pk__in=[self.inactive.pk, other_inactive.pk])
        activate_selected(None, self._request(), queryset)

        self.inactive.refresh_from_db()
        other_inactive.refresh_from_db()
        # First call failed (state untouched), second succeeded despite it.
        self.assertFalse(self.inactive.is_schedule_active)
        self.assertTrue(other_inactive.is_schedule_active)

    @patch("backend.apps.admin_data_tools.schedule_actions.Prefect3Client")
    def test_save_model_arms_via_list_editable_path(self, mock_client):
        """`list_editable` saves through the same `save_model` the change
        form uses — simulate the form reporting the field as changed."""
        model_admin = DisabledFlowScheduleAdmin(DisabledFlowSchedule, None)

        class _Form:
            changed_data = ["is_schedule_active"]

        self.inactive.is_schedule_active = True
        model_admin.save_model(self._request(), self.inactive, _Form(), change=True)

        mock_client.return_value.set_paused.assert_called_once_with("d2", paused=False)
        self.inactive.refresh_from_db()
        self.assertTrue(self.inactive.is_schedule_active)

    @patch("backend.apps.admin_data_tools.schedule_actions.Prefect3Client")
    def test_save_model_does_not_touch_prefect_when_field_unchanged(self, mock_client):
        model_admin = DisabledFlowScheduleAdmin(DisabledFlowSchedule, None)

        class _Form:
            changed_data = []

        model_admin.save_model(self._request(), self.inactive, _Form(), change=True)

        mock_client.return_value.set_paused.assert_not_called()
