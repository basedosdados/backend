# -*- coding: utf-8 -*-
from django.http import JsonResponse
from django.views import View

from backend.apps.api.v1.models import Table
from backend.custom.client import get_gbq_client
from backend.custom.environment import is_prd

from .constants import BQ_LEGACY_TYPE_ALIASES


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
