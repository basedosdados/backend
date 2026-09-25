# -*- coding: utf-8 -*-
"""Tests for the Prefect flow-failure webhook.

This endpoint decides whether a pipeline's schedule gets switched off. Both
failure modes matter: disabling a healthy flow stops data updating, and failing
to disable a broken one leaves it retrying indefinitely. The reactivated_at
guard exists so that an admin who fixes and re-enables a flow does not have it
immediately re-disabled by the failures that preceded the fix.
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from django.test.client import Client

from backend.apps.admin_data_tools.models import DisabledFlowSchedule
from backend.apps.admin_data_tools.views import (
    _after_reactivation,
    _check_bearer_token,
    _is_consecutive_failure,
    _is_dbt_failure,
    _is_dbt_task,
)

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
TOKEN = "test-prefect-key"
WEBHOOK = "/admin-tools/flow-failed/"

HEARTBEAT = "No heartbeat detected from the remote task; marking the run as failed."


def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


def run(state="Failed", at=NOW):
    return {"state_name": state, "start_time": iso(at)}


# ---------------------------------------------------------------------------
# Task name matching
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["run_dbt", "run_dbt-9da", "run_dbt-abc123"])
def test_prefect_hash_suffixes_still_match(name):
    assert _is_dbt_task(name) is True


@pytest.mark.parametrize("name", ["run_dbt_extra", "rundbt", "run_dbtx", "", "dbt"])
def test_other_task_names_do_not_match(name):
    assert _is_dbt_task(name) is False


# ---------------------------------------------------------------------------
# The reactivation guard
# ---------------------------------------------------------------------------


def test_without_a_reactivation_date_every_run_counts():
    assert _after_reactivation(iso(NOW), None) is True


def test_a_run_after_reactivation_counts():
    assert _after_reactivation(iso(NOW), NOW - timedelta(hours=1)) is True


def test_a_run_before_reactivation_does_not_count():
    assert _after_reactivation(iso(NOW), NOW + timedelta(hours=1)) is False


def test_a_run_exactly_at_reactivation_does_not_count():
    """Strictly after, so the boundary is excluded."""
    assert _after_reactivation(iso(NOW), NOW) is False


def test_a_zulu_timestamp_is_parsed():
    assert _after_reactivation("2026-06-01T12:00:00Z", NOW - timedelta(days=1)) is True


# ---------------------------------------------------------------------------
# dbt failures
# ---------------------------------------------------------------------------


def test_a_failed_dbt_task_is_a_dbt_failure():
    tasks = [{"name": "run_dbt", "state_message": "compilation error"}]
    assert _is_dbt_failure(tasks, iso(NOW), None) is True


def test_a_heartbeat_timeout_is_not_a_dbt_failure():
    """Infrastructure flakiness must not switch off a schedule."""
    tasks = [{"name": "run_dbt", "state_message": HEARTBEAT}]
    assert _is_dbt_failure(tasks, iso(NOW), None) is False


def test_a_non_dbt_task_failure_is_not_a_dbt_failure():
    tasks = [{"name": "upload_to_gcs", "state_message": "boom"}]
    assert _is_dbt_failure(tasks, iso(NOW), None) is False


def test_no_failed_tasks_is_not_a_dbt_failure():
    assert _is_dbt_failure([], iso(NOW), None) is False


def test_a_dbt_failure_before_reactivation_is_ignored():
    tasks = [{"name": "run_dbt", "state_message": "compilation error"}]
    assert _is_dbt_failure(tasks, iso(NOW), NOW + timedelta(hours=1)) is False


def test_one_real_dbt_failure_among_ignorable_ones_still_counts():
    tasks = [
        {"name": "run_dbt", "state_message": HEARTBEAT},
        {"name": "run_dbt-9da", "state_message": "compilation error"},
    ]
    assert _is_dbt_failure(tasks, iso(NOW), None) is True


# ---------------------------------------------------------------------------
# Consecutive failures
# ---------------------------------------------------------------------------


def test_two_failures_in_a_row_count():
    assert _is_consecutive_failure([run("Failed"), run("Failed")], None) is True


def test_a_crash_counts_as_a_failure():
    assert _is_consecutive_failure([run("Crashed"), run("Failed")], None) is True


def test_a_success_in_either_slot_breaks_the_streak():
    assert _is_consecutive_failure([run("Completed"), run("Failed")], None) is False
    assert _is_consecutive_failure([run("Failed"), run("Completed")], None) is False


def test_fewer_than_two_runs_is_not_a_streak():
    assert _is_consecutive_failure([], None) is False
    assert _is_consecutive_failure([run("Failed")], None) is False


def test_a_streak_from_before_reactivation_is_ignored():
    runs = [run("Failed", NOW), run("Failed", NOW - timedelta(hours=1))]
    assert _is_consecutive_failure(runs, NOW + timedelta(hours=1)) is False


# ---------------------------------------------------------------------------
# The bearer token guard
# ---------------------------------------------------------------------------


def request_with(auth):
    return MagicMock(META={"HTTP_AUTHORIZATION": auth} if auth is not None else {})


def test_the_matching_bearer_token_is_accepted(monkeypatch):
    monkeypatch.setenv("PREFECT3_API_KEY", TOKEN)
    assert _check_bearer_token(request_with(f"Bearer {TOKEN}")) is True


@pytest.mark.parametrize("auth", ["Bearer wrong", TOKEN, "", None, "Basic x"])
def test_anything_else_is_rejected(monkeypatch, auth):
    monkeypatch.setenv("PREFECT3_API_KEY", TOKEN)
    assert _check_bearer_token(request_with(auth)) is False


def test_an_unset_server_key_rejects_everything(monkeypatch):
    """An empty expected key must never authorise a request."""
    monkeypatch.setenv("PREFECT3_API_KEY", "")
    assert _check_bearer_token(request_with("Bearer ")) is False
    assert _check_bearer_token(request_with("")) is False


# ---------------------------------------------------------------------------
# The webhook endpoint
# ---------------------------------------------------------------------------


@pytest.fixture(name="api_key")
def fixture_api_key(monkeypatch):
    monkeypatch.setenv("PREFECT3_API_KEY", TOKEN)
    return TOKEN


@pytest.fixture(name="record")
def fixture_record():
    return DisabledFlowSchedule.objects.create(
        flow_name="br_ms_sia",
        deployment_id="dep-1",
        is_schedule_active=True,
    )


def post(client, payload, *, token=TOKEN):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
    return client.post(
        WEBHOOK, data=json.dumps(payload), content_type="application/json", **headers
    )


@pytest.mark.django_db
def test_the_webhook_requires_a_token(client: Client, api_key):
    assert post(client, {}, token=None).status_code == 401


@pytest.mark.django_db
def test_the_webhook_rejects_a_wrong_token(client: Client, api_key):
    assert post(client, {}, token="wrong").status_code == 401


@pytest.mark.django_db
def test_the_webhook_rejects_invalid_json(client: Client, api_key):
    response = client.post(
        WEBHOOK,
        data="not json",
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_the_webhook_requires_both_ids(client: Client, api_key):
    assert post(client, {"deployment_id": "dep-1"}).status_code == 400
    assert post(client, {"flow_run_id": "run-1"}).status_code == 400


@pytest.mark.django_db
def test_an_unknown_deployment_is_ignored(client: Client, api_key):
    response = post(client, {"deployment_id": "unknown", "flow_run_id": "run-1"})
    assert response.json() == {"status": "ok", "action": "ignored_unknown"}


@pytest.mark.django_db
def test_an_already_paused_flow_is_left_alone(client: Client, api_key, record):
    record.is_schedule_active = False
    record.save()
    response = post(client, {"deployment_id": "dep-1", "flow_run_id": "run-1"})
    assert response.json() == {"status": "ok", "action": "already_paused"}


@pytest.mark.django_db
@patch("backend.apps.admin_data_tools.views.Prefect3Client")
def test_two_consecutive_failures_disable_the_schedule(
    client_cls: MagicMock, client: Client, api_key, record
):
    prefect = client_cls.return_value
    prefect.get_recent_completed_runs.return_value = [run("Failed"), run("Failed")]
    prefect.get_failed_task_runs.return_value = []

    response = post(client, {"deployment_id": "dep-1", "flow_run_id": "run-1"})

    assert response.json() == {"status": "ok", "action": "disabled"}
    prefect.set_paused.assert_called_once_with("dep-1", paused=True)
    record.refresh_from_db()
    assert record.is_schedule_active is False
    assert record.reactivated_at is None
    assert record.disabled_at is not None


@pytest.mark.django_db
@patch("backend.apps.admin_data_tools.views.Prefect3Client")
def test_a_single_dbt_failure_disables_the_schedule(
    client_cls: MagicMock, client: Client, api_key, record
):
    prefect = client_cls.return_value
    prefect.get_recent_completed_runs.return_value = [run("Failed"), run("Completed")]
    prefect.get_failed_task_runs.return_value = [
        {"name": "run_dbt", "state_message": "compilation error"}
    ]

    response = post(client, {"deployment_id": "dep-1", "flow_run_id": "run-1"})
    assert response.json() == {"status": "ok", "action": "disabled"}


@pytest.mark.django_db
@patch("backend.apps.admin_data_tools.views.Prefect3Client")
def test_an_isolated_non_dbt_failure_takes_no_action(
    client_cls: MagicMock, client: Client, api_key, record
):
    prefect = client_cls.return_value
    prefect.get_recent_completed_runs.return_value = [run("Failed"), run("Completed")]
    prefect.get_failed_task_runs.return_value = [{"name": "upload", "state_message": "boom"}]

    response = post(client, {"deployment_id": "dep-1", "flow_run_id": "run-1"})
    assert response.json() == {"status": "ok", "action": "no_action"}
    prefect.set_paused.assert_not_called()
    record.refresh_from_db()
    assert record.is_schedule_active is True


@pytest.mark.django_db
@patch("backend.apps.admin_data_tools.views.Prefect3Client")
def test_failures_predating_a_reactivation_do_not_re_disable(
    client_cls: MagicMock, client: Client, api_key, record
):
    """An admin fixed the flow and re-enabled it; the old failures must not undo that."""
    record.reactivated_at = NOW + timedelta(hours=1)
    record.save()
    prefect = client_cls.return_value
    prefect.get_recent_completed_runs.return_value = [run("Failed"), run("Failed")]
    prefect.get_failed_task_runs.return_value = [
        {"name": "run_dbt", "state_message": "compilation error"}
    ]

    response = post(client, {"deployment_id": "dep-1", "flow_run_id": "run-1"})
    assert response.json() == {"status": "ok", "action": "no_action"}
    record.refresh_from_db()
    assert record.is_schedule_active is True


@pytest.mark.django_db
def test_the_model_is_named_by_its_flow(record):
    assert str(record) == "br_ms_sia"
