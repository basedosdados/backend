# -*- coding: utf-8 -*-
import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, List

import pandas as pd
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from loguru import logger

from backend.apps.api.v1.models import BigQueryType, Column, Table
from backend.custom.client import get_gbq_client, send_discord_message
from backend.custom.environment import is_prd

from ._prefect3_client import Prefect3Client
from .constants import BQ_LEGACY_TYPE_ALIASES, DBT_TASK_NAMES, FAILED_STATES, STATE_MESSAGES_IGNORE
from .models import DisabledFlowSchedule

logger = logger.bind(module="admin_data_tools")


def _bq_type_to_api_type(field_type: str) -> str:
    """Translate a BigQuery `field.field_type` (legacy name) to the standard
    SQL name used by the API's `bigquery_type` catalog."""
    field_type = field_type.lower()
    return BQ_LEGACY_TYPE_ALIASES.get(field_type, field_type)


def _gbq_slug_for_table(cloud_table) -> str:
    """Full `project.dataset.table` slug for a CloudTable, in the BigQuery
    project matching the current admin environment: `basedosdados` in prod,
    `basedosdados-dev` everywhere else (staging/dev/local) — where the flows
    write before promoting to prod."""
    gcp_project_id = "basedosdados" if is_prd() else "basedosdados-dev"
    return f"{gcp_project_id}.{cloud_table.gcp_dataset_id}.{cloud_table.gcp_table_id}"


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


class ColumnImportError(Exception):
    """Erro de dados na planilha de arquitetura, com mensagem segura pra mostrar ao usuário."""

    def __init__(self, message: str, column_name: str | None = None):
        super().__init__(message)
        self.column_name = column_name


_BQ_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validar_identificador_bq(valor: str, campo: str, column_name: str) -> None:
    """Confere se um valor da planilha é um identificador válido do BigQuery.

    Args:
        valor: Trecho a validar (nome de coluna, dataset ou tabela).
        campo: Descrição do campo de origem, usada na mensagem de erro.
        column_name: Nome da coluna da planilha sendo processada, pra contextualizar o erro.

    Raises:
        ColumnImportError: Se `valor` tiver espaço, ponto ou qualquer caractere fora de
            letras/números/underscore, ou começar com número.
    """
    if not _BQ_IDENTIFIER_RE.match(valor):
        raise ColumnImportError(
            f"{campo} '{valor}' não é um identificador válido do BigQuery — use apenas "
            "letras, números e underscore, sem começar com número (confira se não há "
            "espaços, pontos ou outros caracteres a mais).",
            column_name=column_name,
        )


def _read_architecture_table(url: str) -> pd.DataFrame:
    """Baixa e normaliza a planilha de arquitetura a partir de um link do Google Sheets."""
    id_spreadsheets = url.split("/")[-2]

    spreadsheets_raw_url = (
        f"https://docs.google.com/spreadsheets/d/{id_spreadsheets}/gviz/tq?tqx=out:csv"
    )

    df_architecture = pd.read_csv(spreadsheets_raw_url, dtype=str)
    df_architecture = df_architecture.loc[df_architecture["name"] != "(excluido)"]
    df_architecture.fillna("", inplace=True)

    return df_architecture


def _create_column(selected_table: Table, tables_dict: Dict[str, Table], row: pd.Series) -> Column:
    """Cria uma `Column` a partir de uma linha da planilha de arquitetura.

    Args:
        selected_table: Tabela em que a coluna será criada.
        tables_dict: Mapa `gbq_slug -> Table` de todas as tabelas cadastradas,
            usado pra resolver referências de `directory_column`.
        row: Linha da planilha de arquitetura, já normalizada.

    Returns:
        A `Column` recém-criada (ainda não associada via `.columns.set(...)`).

    Raises:
        ColumnImportError: Se o `bigquery_type`, o nome da coluna ou o
            `directory_column` da linha forem inválidos ou não corresponderem
            a nada cadastrado.
    """
    column_name = row["name"]
    _validar_identificador_bq(column_name, "Nome de coluna", column_name)

    row_bqtype = row["bigquery_type"].strip().upper()
    try:
        bqtype = BigQueryType.objects.get(name=row_bqtype)
    except BigQueryType.DoesNotExist as exc:
        raise ColumnImportError(
            f"Tipo BigQuery '{row_bqtype}' não é reconhecido.", column_name=column_name
        ) from exc

    directory_column = None

    if row["directory_column"]:
        directory_column_raw = row["directory_column"]

        if directory_column_raw.count(":") != 1:
            raise ColumnImportError(
                f"O campo directory_column ('{directory_column_raw}') deveria ter exatamente "
                "um ':' separando a tabela da coluna, no formato 'dataset.tabela:coluna' "
                "(ex.: 'br_bd_diretorios_data_tempo.ano:ano').",
                column_name=column_name,
            )

        table_slug_part, directory_column_name = (
            part.strip() for part in directory_column_raw.split(":")
        )

        if table_slug_part.count(".") != 1:
            raise ColumnImportError(
                f"O campo directory_column ('{directory_column_raw}') deveria referenciar a "
                "tabela como 'dataset.tabela' (um único ponto), no formato "
                "'dataset.tabela:coluna' (ex.: 'br_bd_diretorios_data_tempo.ano:ano').",
                column_name=column_name,
            )

        dataset_slug, table_slug = (part.strip() for part in table_slug_part.split("."))
        _validar_identificador_bq(dataset_slug, "Dataset em directory_column", column_name)
        _validar_identificador_bq(table_slug, "Tabela em directory_column", column_name)
        _validar_identificador_bq(directory_column_name, "Coluna em directory_column", column_name)

        table_full_slug = f"basedosdados.{table_slug_part}"

        try:
            table_directory = tables_dict[table_full_slug]
        except KeyError as exc:
            raise ColumnImportError(
                f"Nenhuma tabela cadastrada corresponde a '{table_full_slug}'.",
                column_name=column_name,
            ) from exc

        try:
            directory_column = table_directory.columns.get(name=directory_column_name)
        except Column.DoesNotExist as exc:
            raise ColumnImportError(
                f"Coluna '{directory_column_name}' não encontrada na tabela de diretório "
                f"'{table_full_slug}'.",
                column_name=column_name,
            ) from exc

    return selected_table.columns.create(
        name=row["name"],
        description=row["description"],
        covered_by_dictionary=row["covered_by_dictionary"] == "yes",
        measurement_unit=row["measurement_unit"],
        contains_sensitive_data=row["has_sensitive_data"] == "yes",
        observations=row["observations"],
        bigquery_type=bqtype,
        directory_primary_key=directory_column,
    )


class UploadColumnsView(View):
    """Importa colunas de uma tabela a partir de uma planilha de arquitetura do Google Sheets.

    Acionada pelo botão "Importar Colunas" na página de admin de uma `Table`
    (``backend/templates/admin/change_form.html``) via
    ``POST /admin-tools/upload-columns/``.

    Substitui as colunas existentes da tabela dentro de uma transação — se
    qualquer linha da planilha falhar (tipo BigQuery desconhecido, nome de
    coluna ou `directory_column` inválido, referência a uma tabela de
    diretório inexistente), nenhuma coluna é perdida.
    """

    def post(self, request):
        """Handle the upload-columns request.

        Args:
            request: Incoming Django HTTP request, com ``table_id`` e
                ``link_arquitetura`` no POST.

        Returns:
            ``JsonResponse`` com ``status`` ("sucesso" ou "erro"). Em erro,
            também traz ``erro`` (mensagem) e, quando aplicável, ``coluna``
            (nome da coluna da planilha que causou o problema).
        """
        table_id = request.POST.get("table_id")
        link = request.POST.get("link_arquitetura")

        try:
            selected_table = Table.objects.get(id=table_id)
        except Table.DoesNotExist:
            return JsonResponse(
                {"status": "erro", "erro": f"Tabela com ID '{table_id}' não encontrada."}
            )

        try:
            architecture = _read_architecture_table(link)
        except Exception as exc:
            return JsonResponse(
                {
                    "status": "erro",
                    "erro": f"Não foi possível ler a planilha de arquitetura: {exc}",
                }
            )

        tables_dict: Dict[str, Table] = {table.gbq_slug: table for table in Table.objects.all()}

        try:
            with transaction.atomic():
                selected_table.columns.all().delete()

                columns: List[Column] = [
                    _create_column(selected_table=selected_table, tables_dict=tables_dict, row=row)
                    for _, row in architecture.iterrows()
                ]

                selected_table.columns.set(columns)
        except ColumnImportError as exc:
            return JsonResponse({"status": "erro", "erro": str(exc), "coluna": exc.column_name})
        except Exception as exc:
            logger.error(f"Falha inesperada ao importar colunas da tabela {table_id}: {exc}")
            return JsonResponse(
                {"status": "erro", "erro": f"Erro inesperado ao importar colunas: {exc}"}
            )

        return JsonResponse({"status": "sucesso", "mensagem": "Colunas salvas com sucesso!"})
