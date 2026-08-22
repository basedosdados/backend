# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime, timezone

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from loguru import logger

from backend.apps.api.v1.models import Table
from backend.custom.client import get_gbq_client
from backend.custom.environment import is_prd

from ._prefect3_client import Prefect3Client
from .models import DisabledFlowSchedule

logger = logger.bind(module="admin_data_tools")

# field.field_type (BigQuery client) reports legacy SQL names (INTEGER,
# FLOAT, RECORD, ...); the API's `bigquery_type` catalog uses standard SQL
# names (INT64, FLOAT64, STRUCT, BOOLEAN, ...) — only these three actually
# differ, everything else (STRING, BOOLEAN, DATE, TIMESTAMP, ...) is spelled
# the same on both sides.
_BQ_LEGACY_TYPE_ALIASES: dict[str, str] = {
    "integer": "int64",
    "float": "float64",
    "record": "struct",
}


def _bq_type_to_api_type(field_type: str) -> str:
    """Translate a BigQuery `field.field_type` (legacy name) to the standard
    SQL name used by the API's `bigquery_type` catalog."""
    field_type = field_type.lower()
    return _BQ_LEGACY_TYPE_ALIASES.get(field_type, field_type)


def _gbq_slug_for_table(cloud_table) -> str:
    """Full `project.dataset.table` slug for a CloudTable, in the BigQuery
    project matching the current admin environment: `basedosdados` in prod,
    `basedosdados-dev` everywhere else (staging/dev/local) — where the flows
    write before promoting to prod."""
    gcp_project_id = "basedosdados" if is_prd() else "basedosdados-dev"
    return f"{gcp_project_id}.{cloud_table.gcp_dataset_id}.{cloud_table.gcp_table_id}"


_FAILED_STATES = {"Failed", "Crashed"}
_DBT_TASK_NAMES = {"run_dbt"}
_STATE_MESSAGES_IGNORE = {
    "No heartbeat detected from the remote task; marking the run as failed.",
}


def _is_dbt_task(name: str) -> bool:
    # Prefect 3 appends a short hash suffix to task names (e.g. run_dbt-9da)
    return any(name == n or name.startswith(f"{n}-") for n in _DBT_TASK_NAMES)


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
        _is_dbt_task(t.get("name", "")) and t.get("state_message", "") not in _STATE_MESSAGES_IGNORE
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

    if last["state_name"] not in _FAILED_STATES or prev["state_name"] not in _FAILED_STATES:
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

    For each deployment returned by the Prefect 3 API:

    - If the deployment is unknown: creates a ``DisabledFlowSchedule`` record
      with ``is_schedule_active=False`` (stays paused).
    - If the deployment is known: updates ``deployment_id`` if it changed after
      re-deploy, then enforces the stored ``is_schedule_active`` state in Prefect 3.
    """

    def post(self, request):
        """Handle the sync request.

        Args:
            request: Incoming Django HTTP request. Must carry a valid bearer token
                in the ``Authorization`` header.

        Returns:
            ``JsonResponse`` with a summary dict containing counts for
            ``created``, ``updated``, ``activated``, ``paused``, and ``errors``.
            Returns 401 if the bearer token is invalid.
        """
        if not _check_bearer_token(request):
            return JsonResponse({"error": "Unauthorized"}, status=401)

        client = Prefect3Client()
        results = {"created": 0, "updated": 0, "activated": 0, "paused": 0, "errors": 0}

        for dep in client.iter_deployments():
            name = dep["name"]
            dep_id = dep["id"]
            currently_paused = dep.get("paused", False)
            try:
                self._sync_deployment(client, name, dep_id, currently_paused, results)
            except Exception as exc:
                logger.error(f"Error syncing deployment {name}: {exc}")
                results["errors"] += 1

        logger.info(f"Sync complete: {results}")
        return JsonResponse(results)

    def _sync_deployment(self, client, name, dep_id, currently_paused, results):
        """Sync a single deployment against the database and Prefect 3.

        Only calls ``set_paused`` when the current Prefect state differs from
        the desired state, avoiding unnecessary API calls on every sync.

        Args:
            client: Authenticated ``Prefect3Client`` instance.
            name: Deployment name as returned by the Prefect 3 API.
            dep_id: Deployment UUID as returned by the Prefect 3 API.
            currently_paused: Current paused state of the deployment in Prefect 3.
            results: Mutable summary dict updated in place.
        """
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
            DisabledFlowSchedule.objects.create(
                flow_name=name,
                deployment_id=dep_id,
                is_schedule_active=False,
            )
            results["created"] += 1


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

    The disable logic (validation of consecutive failures and pausing the
    deployment) will be implemented in block 5 and wired here.
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
        should_disable = _is_consecutive_failure(runs, record.reactivated_at) or (
            current_run_start
            and _is_dbt_failure(task_runs, current_run_start, record.reactivated_at)
        )

        if should_disable:
            client.set_paused(deployment_id, paused=True)
            record.is_schedule_active = False
            record.reactivated_at = None
            record.disabled_at = datetime.now(tz=timezone.utc)
            record.save(update_fields=["is_schedule_active", "reactivated_at", "disabled_at"])
            logger.info(f"Disabled {record.flow_name} after failure")
            return JsonResponse({"status": "ok", "action": "disabled"})

        return JsonResponse({"status": "ok", "action": "no_action"})


class CheckMetadadosView(View):
    """Compara o schema real da tabela no BigQuery com as colunas cadastradas na API.

    Acionada pelo botão "Checar Metadados" na página de admin de uma `Table`
    (``backend/templates/admin/change_form.html``) via
    ``POST /admin-tools/check-metadados/``. Mesma checagem do
    ``.github/workflows/scripts/check_metadata.py`` (repo pipelines), mas lendo
    ``bq_client.get_table(...).schema`` em vez de consultar `INFORMATION_SCHEMA`
    — é metadado da tabela, não uma query faturada.

    Chamada de dentro do admin autenticado (não machine-to-machine como as
    demais views deste módulo), então mantém a proteção de CSRF padrão do
    Django em vez do bearer token usado acima.

    Compara sempre contra o projeto do BigQuery correspondente ao ambiente do
    próprio admin (``is_prd()``): em staging/dev contra ``basedosdados-dev``
    — onde os flows escrevem antes de promover pra prod —, em prod contra
    ``basedosdados``. Sem isso, staging acabaria comparando contra dados que
    ainda nem foram promovidos.
    """

    def post(self, request):
        """Handle the check-metadados request.

        Args:
            request: Incoming Django HTTP request, com ``table_id`` no POST.

        Returns:
            ``JsonResponse`` com ``status`` ("sucesso" ou "erro") e
            ``discrepancias``, uma lista de objetos ``{coluna, tipo, ...}`` —
            ``tipo`` é um de ``somente_bigquery``, ``somente_api``,
            ``tipo_diferente`` ou ``descricao_diferente``; os dois últimos
            também trazem ``bigquery``/``api`` com os valores comparados.
        """
        table_id = request.POST.get("table_id")
        selected_table = Table.objects.get(id=table_id)

        cloud_table = selected_table.cloud_tables.first()
        if not cloud_table:
            return JsonResponse(
                {
                    "status": "erro",
                    "erro": "Tabela sem CloudTable vinculada — não é possível checar o BigQuery.",
                }
            )

        gbq_slug = _gbq_slug_for_table(cloud_table)

        try:
            bq_client = get_gbq_client()
            bq_table = bq_client.get_table(gbq_slug)
        except Exception as exc:
            return JsonResponse({"status": "erro", "erro": f"Falha ao consultar o BigQuery: {exc}"})

        bq_columns = {field.name.lower(): field for field in bq_table.schema}
        db_columns = {column.name.lower(): column for column in selected_table.columns.all()}

        discrepancias: list[dict] = []

        for name, field in bq_columns.items():
            column = db_columns.get(name)
            if column is None:
                discrepancias.append({"coluna": field.name, "tipo": "somente_bigquery"})
                continue

            bq_type = (field.field_type or "").upper()
            api_type = (column.bigquery_type.name if column.bigquery_type else "").lower()
            if _bq_type_to_api_type(bq_type) != api_type:
                discrepancias.append(
                    {
                        "coluna": field.name,
                        "tipo": "tipo_diferente",
                        "bigquery": bq_type,
                        "api": api_type.upper(),
                    }
                )

            bq_desc = field.description or ""
            api_desc = column.description or ""
            if bq_desc != api_desc:
                discrepancias.append(
                    {
                        "coluna": field.name,
                        "tipo": "descricao_diferente",
                        "bigquery": bq_desc,
                        "api": api_desc,
                    }
                )

        for name, column in db_columns.items():
            if name not in bq_columns:
                discrepancias.append({"coluna": column.name, "tipo": "somente_api"})

        status = "erro" if discrepancias else "sucesso"
        return JsonResponse({"status": status, "discrepancias": discrepancias})


class SyncUpdateLatestView(View):
    """Sincroniza `Update.latest` (ancorado na Table) com o `last_modified`
    real do BigQuery.

    Acionada pelo botão "Sync latest do BigQuery", ao lado do "Update and
    Poll Info" na página de admin de uma `Table`
    (``backend/apps/api/v1/admin.py::TableAdmin.get_update_display``). Só
    faz sentido pro Update ancorado na própria Table — o Update do
    RawDataSource guarda a data de competência publicada pela fonte, não
    wall-clock, então não tem o que sincronizar contra o BigQuery ali.

    Corrige na hora um `Table.Update.latest` desatualizado sem precisar
    esperar o próximo flow rodar (mesmo problema resolvido em pipelines#1883
    para os flows que ainda usavam `poll.py`).
    """

    def post(self, request):
        table_id = request.POST.get("table_id")
        selected_table = Table.objects.get(id=table_id)

        cloud_table = selected_table.cloud_tables.first()
        if not cloud_table:
            return JsonResponse(
                {
                    "status": "erro",
                    "erro": (
                        "Tabela sem CloudTable vinculada — não é possível consultar o BigQuery."
                    ),
                }
            )

        updates = list(selected_table.updates.all())
        if len(updates) != 1:
            return JsonResponse(
                {
                    "status": "erro",
                    "erro": (
                        f"Tabela tem {len(updates)} Update(s) vinculado(s) — só sincroniza "
                        "quando há exatamente 1. Resolva a ambiguidade na aba Updates antes."
                    ),
                }
            )
        update = updates[0]

        gbq_slug = _gbq_slug_for_table(cloud_table)

        try:
            bq_client = get_gbq_client()
            bq_table = bq_client.get_table(gbq_slug)
        except Exception as exc:
            return JsonResponse({"status": "erro", "erro": f"Falha ao consultar o BigQuery: {exc}"})

        if not bq_table.modified:
            return JsonResponse(
                {"status": "erro", "erro": "BigQuery não informou last_modified para essa tabela."}
            )

        update.latest = bq_table.modified
        update.save(update_fields=["latest"])

        return JsonResponse(
            {
                "status": "sucesso",
                "mensagem": f"Update.latest sincronizado: {bq_table.modified.isoformat()}",
            }
        )
