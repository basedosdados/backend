# -*- coding: utf-8 -*-
"""Tests for the admin_data_tools endpoints."""

import json
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import DisabledFlowSchedule

TOKEN = "test-token"
AUTH = {"HTTP_AUTHORIZATION": f"Bearer {TOKEN}"}


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
    @patch("backend.apps.admin_data_tools.views.Prefect3Client")
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
    @patch("backend.apps.admin_data_tools.views.Prefect3Client")
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
    @patch("backend.apps.admin_data_tools.views.Prefect3Client")
    def test_setting_current_state_is_a_safe_noop(self, mock_client):
        """Doubles as the auth smoke test: reaches the view, touches nothing."""
        resp = self._post({"flow_name": self.record.flow_name, "is_schedule_active": False}, **AUTH)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["action"], "no_change")
        mock_client.return_value.set_paused.assert_not_called()

    @patch.dict("os.environ", {"PREFECT3_API_KEY": TOKEN})
    @patch("backend.apps.admin_data_tools.views.Prefect3Client")
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
    @patch("backend.apps.admin_data_tools.views.Prefect3Client")
    def test_bad_token_is_rejected_before_any_write(self, mock_client):
        resp = self._post(
            {"flow_name": self.record.flow_name, "is_schedule_active": True},
            HTTP_AUTHORIZATION="Bearer wrong",
        )
        self.assertEqual(resp.status_code, 401)
        mock_client.return_value.set_paused.assert_not_called()
        self.record.refresh_from_db()
        self.assertFalse(self.record.is_schedule_active)
