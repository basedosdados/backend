# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime, timezone

from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from loguru import logger

from backend.apps.api.v1.models import CloudTable, Table
from backend.custom.client import send_discord_message

from ._prefect3_client import Prefect3Client
from .constants import DBT_TASK_NAMES, FAILED_STATES, STATE_MESSAGES_IGNORE
from .models import DisabledFlowSchedule
from .schedule_actions import apply_schedule_state

logger = logger.bind(module="admin_data_tools.flow_monitoring")


def _single_table_candidates(name: str, tags: list[str]) -> list[str]:
    """Build candidate dataset/table strings for a deployment.

    Args:
        name: Deployment name as returned by the Prefect 3 API.
        tags: Deployment tags as returned by the Prefect 3 API.

    Returns:
        Every string from ``name``/``tags`` containing a double underscore.
    """
    candidates = [t for t in tags if "__" in t]
    if "__" in name:
        candidates.append(name)
    return candidates


def _build_cloud_table_index() -> tuple[dict[tuple[str, str], object], dict[str, set]]:
    """Load every ``CloudTable`` once, indexed for deployment resolution.

    Loading this in a single query up front — instead of one ``CloudTable``
    query per deployment — is what keeps a full sync (hundreds of
    deployments) from timing out behind the nginx gateway.

    Returns:
        A tuple of:
        - ``{(gcp_dataset_id, gcp_table_id): table_id}``, for a deployment's
          specific dataset/table match.
        - ``{gcp_dataset_id: {table_id, ...}}``, for the monolithic
          dataset-wide fallback.
    """
    by_dataset_table = {}
    by_dataset = {}
    for gcp_dataset_id, gcp_table_id, table_id in CloudTable.objects.values_list(
        "gcp_dataset_id", "gcp_table_id", "table_id"
    ):
        by_dataset_table[(gcp_dataset_id, gcp_table_id)] = table_id
        by_dataset.setdefault(gcp_dataset_id, set()).add(table_id)
    return by_dataset_table, by_dataset


def _resolve_single_table_id(name: str, tags: list[str], by_dataset_table: dict) -> object | None:
    """Resolve the id of the single table a deployment's name/tags point to.

    Args:
        name: Deployment name as returned by the Prefect 3 API.
        tags: Deployment tags as returned by the Prefect 3 API.
        by_dataset_table: ``{(gcp_dataset_id, gcp_table_id): table_id}``, from
            ``_build_cloud_table_index``.

    Returns:
        The matching ``Table.id``, or ``None`` if no candidate matches a
        known ``CloudTable``.
    """
    for candidate in _single_table_candidates(name, tags):
        dataset_id, _, table_id = candidate.partition("__")
        match = by_dataset_table.get((dataset_id, table_id))
        if match:
            return match
    return None


def _dedicated_table_ids(deployments: list[dict], by_dataset_table: dict) -> set:
    """Collect every table id already resolved to a specific deployment.

    Args:
        deployments: Deployment dicts as returned by the Prefect 3 API.
        by_dataset_table: ``{(gcp_dataset_id, gcp_table_id): table_id}``, from
            ``_build_cloud_table_index``.

    Returns:
        Set of ``Table.id`` values resolved via ``_resolve_single_table_id``
        across all given deployments.
    """
    ids = set()
    for dep in deployments:
        table_id = _resolve_single_table_id(dep["name"], dep.get("tags") or [], by_dataset_table)
        if table_id:
            ids.add(table_id)
    return ids


def _resolve_table_ids(
    name: str,
    tags: list[str],
    by_dataset_table: dict,
    by_dataset: dict,
    dedicated_table_ids: set,
) -> list:
    """Resolve the id(s) of the table(s) a deployment feeds.

    Args:
        name: Deployment name as returned by the Prefect 3 API.
        tags: Deployment tags as returned by the Prefect 3 API.
        by_dataset_table: ``{(gcp_dataset_id, gcp_table_id): table_id}``, from
            ``_build_cloud_table_index``.
        by_dataset: ``{gcp_dataset_id: {table_id, ...}}``, from
            ``_build_cloud_table_index``.
        dedicated_table_ids: ``Table.id`` values already claimed by another
            deployment's specific dataset/table match.

    Returns:
        A single-element list when a specific dataset/table match is found;
        every table id under the deployment's dataset, minus
        ``dedicated_table_ids``, when there's no such match at all; ``[]``
        otherwise.
    """
    candidates = _single_table_candidates(name, tags)
    if candidates:
        table_id = _resolve_single_table_id(name, tags, by_dataset_table)
        return [table_id] if table_id else []

    dataset_id = name.removesuffix("_flow")
    return [tid for tid in by_dataset.get(dataset_id, ()) if tid not in dedicated_table_ids]


def _is_dbt_task(name: str) -> bool:
    # Prefect 3 appends a short hash suffix to task names (e.g. run_dbt-9da)
    return any(name == n or name.startswith(f"{n}-") for n in DBT_TASK_NAMES)


def _after_reactivation(start_time_iso: str, reactivated_at) -> bool:
    """Return True if start_time_iso is strictly after reactivated_at.

    Args:
        start_time_iso: ISO 8601 start timestamp string from Prefect 3.
        reactivated_at: Datetime the flow was last reactivated, or ``None``.

    Returns:
        ``True`` if no reactivation date is set or the run started after it.
    """
    if not reactivated_at:
        return True
    start = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
    return start.astimezone(timezone.utc) > reactivated_at.astimezone(timezone.utc)


def _is_dbt_failure(task_runs: list[dict], run_start_time: str, reactivated_at) -> bool:
    """Return True if a run_dbt task failed with a non-ignorable error after reactivation.

    Args:
        task_runs: Failed task runs for the current flow run, as returned by
            ``Prefect3Client.get_failed_task_runs``.
        run_start_time: ISO 8601 start time of the flow run.
        reactivated_at: Datetime the flow was last reactivated, or ``None``.

    Returns:
        ``True`` if any task named ``run_dbt`` failed with a non-ignorable
        state message and the run occurred after ``reactivated_at``.
    """
    if not _after_reactivation(run_start_time, reactivated_at):
        return False
    return any(
        _is_dbt_task(t.get("name", "")) and t.get("state_message", "") not in STATE_MESSAGES_IGNORE
        for t in task_runs
    )


def _is_consecutive_failure(runs: list[dict], reactivated_at) -> bool:
    """Return True if the last two completed runs both failed after reactivation.

    Args:
        runs: Last two completed flow runs ordered by start time descending,
            as returned by ``Prefect3Client.get_recent_completed_runs``.
        reactivated_at: Datetime the flow was last reactivated by an admin, or
            ``None`` if no reactivation has been recorded. When set, only failures
            after this timestamp are considered to avoid re-disabling a flow for
            pre-fix failures.

    Returns:
        ``True`` if both runs failed and the most recent one occurred after
        ``reactivated_at`` (or ``reactivated_at`` is ``None``).
    """
    if len(runs) < 2:
        return False

    last, prev = runs[0], runs[1]

    if last["state_name"] not in FAILED_STATES or prev["state_name"] not in FAILED_STATES:
        return False

    return _after_reactivation(last["start_time"], reactivated_at)


def _check_bearer_token(request) -> bool:
    """Validate the Authorization header against PREFECT3_API_KEY.

    Args:
        request: Incoming Django HTTP request.

    Returns:
        ``True`` if the bearer token matches the expected value, ``False`` otherwise.
    """
    expected = os.getenv("PREFECT3_API_KEY", "")
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    return bool(expected and auth == f"Bearer {expected}")


@method_decorator(csrf_exempt, name="dispatch")
class SyncDeploymentsView(View):
    """Sync Prefect 3 deployments with the database.

    Triggered by CI after every deploy via ``POST /admin-tools/sync-deployments/``.

    Deployments with no Prefect schedule attached (e.g. a stage only ever
    triggered via ``run_deployment()`` from another flow, never on a cron) are
    not arming candidates — there is nothing to pause or unpause — so they are
    skipped entirely and never get a ``DisabledFlowSchedule`` row. Any row that
    already exists for one (e.g. its schedule was later removed) is deleted.

    For each remaining (scheduled) deployment returned by the Prefect 3 API:

    - If the deployment is unknown: creates a ``DisabledFlowSchedule`` record
      with ``is_schedule_active=False`` (stays paused).
    - If the deployment is known: updates ``deployment_id`` if it changed after
      re-deploy, then enforces the stored ``is_schedule_active`` state in Prefect 3.

    Also resolves and keeps in sync which ``Table``(s) each deployment feeds
    (see ``_resolve_table_ids``), linking them via ``Table.flow_schedule`` —
    zero, one, or several, depending on what the deployment's tags/name
    resolve to. Zero is the normal case for a flow matching neither naming
    convention, not an error.
    """

    def post(self, request):
        """Handle the sync request.

        Args:
            request: Incoming Django HTTP request. Must carry a valid bearer token
                in the ``Authorization`` header.

        Returns:
            ``JsonResponse`` with a summary dict containing counts for
            ``created``, ``updated``, ``activated``, ``paused``,
            ``removed_no_schedule``, ``tables_linked``, and ``errors``.
            Returns 401 if the bearer token is invalid.
        """
        if not _check_bearer_token(request):
            return JsonResponse({"error": "Unauthorized"}, status=401)

        client = Prefect3Client()
        # Materialized once (not a generator pass-through): needed twice,
        # first to find every table with a dedicated flow across the whole
        # batch, then to actually sync — order Prefect returns deployments
        # in must never affect the outcome.
        deployments = list(client.iter_deployments())
        # One query for every CloudTable up front, instead of one per
        # deployment — with hundreds of deployments the per-deployment
        # queries pushed the whole sync past the nginx gateway timeout.
        by_dataset_table, by_dataset = _build_cloud_table_index()
        dedicated_table_ids = _dedicated_table_ids(deployments, by_dataset_table)
        results = {
            "created": 0,
            "updated": 0,
            "activated": 0,
            "paused": 0,
            "removed_no_schedule": 0,
            "tables_linked": 0,
            "errors": 0,
        }

        for dep in deployments:
            name = dep["name"]
            dep_id = dep["id"]
            currently_paused = dep.get("paused", False)
            has_schedule = bool(dep.get("schedules"))
            table_ids = _resolve_table_ids(
                name, dep.get("tags") or [], by_dataset_table, by_dataset, dedicated_table_ids
            )
            try:
                self._sync_deployment(
                    client, name, dep_id, currently_paused, has_schedule, table_ids, results
                )
            except Exception as exc:
                logger.error(f"Error syncing deployment {name}: {exc}")
                results["errors"] += 1

        logger.info(f"Sync complete: {results}")
        return JsonResponse(results)

    def _sync_deployment(
        self, client, name, dep_id, currently_paused, has_schedule, table_ids, results
    ):
        """Sync a single deployment against the database and Prefect 3.

        Only calls ``set_paused`` when the current Prefect state differs from
        the desired state, avoiding unnecessary API calls on every sync.

        Args:
            client: Authenticated ``Prefect3Client`` instance.
            name: Deployment name as returned by the Prefect 3 API.
            dep_id: Deployment UUID as returned by the Prefect 3 API.
            currently_paused: Current paused state of the deployment in Prefect 3.
            has_schedule: Whether the deployment has at least one Prefect schedule.
            table_ids: Ids of the ``Table``s this deployment feeds, from
                ``_resolve_table_ids`` — zero, one, or several.
            results: Mutable summary dict updated in place.
        """
        if not has_schedule:
            deleted, _ = DisabledFlowSchedule.objects.filter(flow_name=name).delete()
            if deleted:
                results["removed_no_schedule"] += 1
            return

        try:
            record = DisabledFlowSchedule.objects.get(flow_name=name)
            if record.deployment_id != dep_id:
                record.deployment_id = dep_id
                record.save(update_fields=["deployment_id"])
                results["updated"] += 1
            should_be_paused = not record.is_schedule_active
            if should_be_paused != currently_paused:
                client.set_paused(dep_id, paused=should_be_paused)
            if should_be_paused:
                results["paused"] += 1
            else:
                results["activated"] += 1
        except DisabledFlowSchedule.DoesNotExist:
            record = DisabledFlowSchedule.objects.create(
                flow_name=name,
                deployment_id=dep_id,
                is_schedule_active=False,
            )
            results["created"] += 1

        if table_ids:
            results["tables_linked"] += (
                Table.objects.filter(id__in=table_ids)
                .exclude(flow_schedule_id=record.id)
                .update(flow_schedule_id=record.id)
            )


@method_decorator(csrf_exempt, name="dispatch")
class FlowFailedWebhookView(View):
    """Receive failure notifications from Prefect 3 automations.

    Called by a Prefect 3 automation on ``prefect.flow-run.Failed`` events
    via ``POST /admin-tools/flow-failed/``.

    Expected JSON payload (configured in the Prefect 3 automation)::

        {
            "deployment_id": "{{ deployment.id }}",
            "flow_run_id": "{{ flow_run.id }}",
            "flow_run_name": "{{ flow_run.name }}"
        }

    Validates consecutive failures / dbt task failures, pauses the deployment
    in Prefect 3, and posts a message to Discord with the cause.
    """

    def post(self, request):
        """Handle the flow-failed webhook.

        Args:
            request: Incoming Django HTTP request. Must carry a valid bearer
                token in the ``Authorization`` header.

        Returns:
            ``JsonResponse`` with ``{"status": "ok"}`` on success.
            Returns 400 if the payload is missing required fields.
            Returns 401 if the bearer token is invalid.
        """
        if not _check_bearer_token(request):
            return JsonResponse({"error": "Unauthorized"}, status=401)

        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        deployment_id = payload.get("deployment_id")
        flow_run_id = payload.get("flow_run_id")
        flow_run_name = payload.get("flow_run_name", "")

        if not deployment_id or not flow_run_id:
            return JsonResponse({"error": "deployment_id and flow_run_id are required"}, status=400)

        logger.info(
            f"Flow failed webhook received | deployment={deployment_id} "
            f"flow_run={flow_run_name} ({flow_run_id})"
        )

        try:
            record = DisabledFlowSchedule.objects.get(deployment_id=deployment_id)
        except DisabledFlowSchedule.DoesNotExist:
            logger.warning(f"Unknown deployment {deployment_id} — ignoring")
            return JsonResponse({"status": "ok", "action": "ignored_unknown"})

        if not record.is_schedule_active:
            return JsonResponse({"status": "ok", "action": "already_paused"})

        client = Prefect3Client()
        runs = client.get_recent_completed_runs(deployment_id, limit=2)
        task_runs = client.get_failed_task_runs(flow_run_id)

        current_run_start = runs[0]["start_time"] if runs else None
        consecutive_failure = _is_consecutive_failure(runs, record.reactivated_at)
        dbt_failure = bool(
            current_run_start
            and _is_dbt_failure(task_runs, current_run_start, record.reactivated_at)
        )

        if consecutive_failure or dbt_failure:
            client.set_paused(deployment_id, paused=True)
            record.is_schedule_active = False
            record.reactivated_at = None
            record.disabled_at = datetime.now(tz=timezone.utc)
            record.save(update_fields=["is_schedule_active", "reactivated_at", "disabled_at"])
            logger.info(f"Disabled {record.flow_name} after failure")
            self._notify_disabled(record, consecutive_failure, dbt_failure)
            return JsonResponse({"status": "ok", "action": "disabled"})

        return JsonResponse({"status": "ok", "action": "no_action"})

    @staticmethod
    def _notify_disabled(
        record: DisabledFlowSchedule, consecutive_failure: bool, dbt_failure: bool
    ) -> None:
        """Post a Discord message with the flow name and the cause of the disable.

        Args:
            record: The ``DisabledFlowSchedule`` just paused.
            consecutive_failure: Whether the last two completed runs both failed.
            dbt_failure: Whether a ``run_dbt`` task failed in the triggering run.
        """
        if consecutive_failure and dbt_failure:
            cause = "2 execuções consecutivas falharam, incluindo uma falha de task dbt"
        elif consecutive_failure:
            cause = "2 execuções consecutivas falharam"
        else:
            cause = "uma task dbt (`run_dbt`) falhou"

        change_url = settings.BACKEND_URL + reverse(
            "admin:admin_data_tools_disabledflowschedule_change", args=[record.pk]
        )
        prefect_ui_url = settings.PREFECT3_API_URL.removesuffix("/api")
        deployment_url = (
            f"{prefect_ui_url}/v2/deployments/deployment/{record.deployment_id}?tab=Runs"
        )

        send_discord_message(
            f"<@&{settings.DISCORD_DADOS_TEAM_ROLE_ID}>\n"
            f"🔴 Pipeline desativada automaticamente: **{record.flow_name}**\n"
            f"Motivo: {cause}\n"
            f"[Ver no admin]({change_url}) · [Ver no Prefect]({deployment_url})"
        )


@method_decorator(csrf_exempt, name="dispatch")
class SetScheduleActiveView(View):
    """Arm or disarm a flow schedule, programmatically.

    Called via ``POST /admin-tools/set-schedule-active/``. This is the API
    equivalent of ticking ``is_schedule_active`` in the Django admin, and it
    performs the same three steps as ``DisabledFlowScheduleAdmin.save_model``:
    it updates the stored state, stamps ``reactivated_at``, and pauses or
    unpauses the deployment in Prefect 3.

    All three matter. Flipping only Prefect would be undone by the next
    ``SyncDeploymentsView`` run — which CI triggers on every merge to main —
    because sync enforces the stored ``is_schedule_active`` state.

    Expected JSON payload::

        {"flow_name": "<deployment name>", "is_schedule_active": true}

    Setting the state a flow is already in is a safe no-op: it returns
    ``action="no_change"`` without calling Prefect, mirroring the admin form,
    which only acts when the field actually changes.
    """

    def post(self, request):
        """Handle the set-schedule-active request.

        Args:
            request: Incoming Django HTTP request. Must carry a valid bearer
                token in the ``Authorization`` header.

        Returns:
            ``JsonResponse`` describing the resulting state, with ``action``
            one of ``activated``, ``disabled`` or ``no_change``.
            Returns 400 if the payload is missing or malformed, 401 if the
            bearer token is invalid, and 404 if the flow is unknown.
        """
        if not _check_bearer_token(request):
            return JsonResponse({"error": "Unauthorized"}, status=401)

        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        flow_name = payload.get("flow_name")
        desired = payload.get("is_schedule_active")

        if not flow_name or not isinstance(desired, bool):
            return JsonResponse(
                {"error": "flow_name (str) and is_schedule_active (bool) are required"},
                status=400,
            )

        try:
            record = DisabledFlowSchedule.objects.get(flow_name=flow_name)
        except DisabledFlowSchedule.DoesNotExist:
            return JsonResponse(
                {
                    "error": (
                        f"Unknown flow {flow_name!r}. Deployments are registered by "
                        "POST /admin-tools/sync-deployments/, which CI runs after "
                        "each deploy to main."
                    )
                },
                status=404,
            )

        if record.is_schedule_active == desired:
            return JsonResponse(
                {
                    "flow_name": record.flow_name,
                    "deployment_id": record.deployment_id,
                    "is_schedule_active": record.is_schedule_active,
                    "reactivated_at": (
                        record.reactivated_at.isoformat() if record.reactivated_at else None
                    ),
                    "action": "no_change",
                }
            )

        apply_schedule_state(record, desired)

        action = "activated" if desired else "disabled"
        logger.info(f"{action} {record.flow_name} via set-schedule-active")

        return JsonResponse(
            {
                "flow_name": record.flow_name,
                "deployment_id": record.deployment_id,
                "is_schedule_active": record.is_schedule_active,
                "reactivated_at": (
                    record.reactivated_at.isoformat() if record.reactivated_at else None
                ),
                "action": action,
            }
        )
