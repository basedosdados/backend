# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from datetime import timedelta
from typing import Dict, List
from urllib.parse import urlparse

import pandas as pd
from django.core.serializers import serialize
from django.db import transaction
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.views import View
from loguru import logger

from backend.apps.api.v1.models import (
    BigQueryType,
    CloudTable,
    Column,
    Dataset,
    Table,
    get_temporal_coverage,
)

logger = logger.bind(module="api_v1")

URL_MAPPING = {
    "localhost:8080": "http://localhost:3000",
    "backend.basedosdados.org": "https://basedosdados.org",
    "staging.backend.basedosdados.org": "https://staging.basedosdados.org",
    "development.backend.basedosdados.org": "https://development.basedosdados.org",
}


class DatasetRedirectView(View):
    """View to redirect old dataset urls"""

    def get(self, request, *args, **kwargs):
        """Redirect to new dataset url"""
        url = request.build_absolute_uri()
        domain = URL_MAPPING[urlparse(url).netloc]

        if dataset := request.GET.get("dataset"):
            dataset_slug = dataset.replace("-", "_")

            if resource := CloudTable.objects.filter(gcp_dataset_id=dataset_slug).first():
                return HttpResponseRedirect(f"{domain}/dataset/{resource.table.dataset.id}")

            if resource := Dataset.objects.filter(slug__icontains=dataset_slug).first():
                return HttpResponseRedirect(f"{domain}/dataset/{resource.id}")

        return HttpResponseRedirect(f"{domain}/404")


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


def upload_columns(request: HttpRequest):
    _token, table_id, _dataset_id, link = request.POST.values()

    try:
        selected_table = Table.objects.get(id=table_id)
    except Table.DoesNotExist:
        return JsonResponse(
            {"status": "erro", "erro": f"Tabela com ID '{table_id}' não encontrada."},
            status=400,
        )

    try:
        architecture = read_architecture_table(link)
    except Exception as exc:
        logger.error(f"Falha ao ler planilha de arquitetura '{link}': {exc}")
        return JsonResponse(
            {"status": "erro", "erro": f"Não foi possível ler a planilha de arquitetura: {exc}"},
            status=400,
        )

    tables_dict: Dict[str, Table] = {table.gbq_slug: table for table in Table.objects.all()}

    try:
        with transaction.atomic():
            selected_table.columns.all().delete()

            columns: List[Column] = [
                create_columns(selected_table=selected_table, tables_dict=tables_dict, row=row)
                for _, row in architecture.iterrows()
            ]

            selected_table.columns.set(columns)
    except ColumnImportError as exc:
        return JsonResponse(
            {"status": "erro", "erro": str(exc), "coluna": exc.column_name}, status=400
        )
    except Exception as exc:
        logger.error(f"Falha inesperada ao importar colunas da tabela {table_id}: {exc}")
        return JsonResponse(
            {"status": "erro", "erro": f"Erro inesperado ao importar colunas: {exc}"},
            status=500,
        )

    return JsonResponse({"status": "sucesso", "mensagem": "Colunas salvas com sucesso!"})


def read_architecture_table(url: str) -> pd.DataFrame:
    id_spreadsheets = url.split("/")[-2]

    spreadsheets_raw_url = (
        f"https://docs.google.com/spreadsheets/d/{id_spreadsheets}/gviz/tq?tqx=out:csv"
    )

    df_architecture = pd.read_csv(spreadsheets_raw_url, dtype=str)

    df_architecture = df_architecture.loc[df_architecture["name"] != "(excluido)"]

    df_architecture.fillna("", inplace=True)

    return df_architecture


def create_columns(selected_table: Table, tables_dict: Dict[str, Table], row: pd.Series) -> Column:
    column_name = row["name"]
    _validar_identificador_bq(column_name, "Nome de coluna", column_name)

    # Pegar ID do BigQueryType Model

    row_bqtype = row["bigquery_type"].strip().upper()
    try:
        bqtype = BigQueryType.objects.get(name=row_bqtype)
    except BigQueryType.DoesNotExist as exc:
        raise ColumnImportError(
            f"Tipo BigQuery '{row_bqtype}' não é reconhecido.", column_name=column_name
        ) from exc

    # Pegar ID da coluna Diretorio

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

    # Definir Coluna

    column = selected_table.columns.create(
        name=row["name"],
        description=row["description"],
        covered_by_dictionary=row["covered_by_dictionary"] == "yes",
        measurement_unit=row["measurement_unit"],
        contains_sensitive_data=row["has_sensitive_data"] == "yes",
        observations=row["observations"],
        bigquery_type=bqtype,
        directory_primary_key=directory_column,
    )

    return column


def table_stats(request: HttpRequest):
    """
    Calculates and returns statistics about the tables and datasets.
    """
    treated_tables = (
        Table.objects.exclude(status__slug__in=["under_review", "excluded"])
        .exclude(slug__in=["dicionario", "dictionary"])
        .exclude(dataset__status__slug__in=["under_review", "excluded"])
    )

    datasets_with_treated_tables_count = (
        treated_tables.values_list("dataset_id", flat=True).distinct().count()
    )

    total_treated_tables_count = treated_tables.count()

    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_tables_count = (
        treated_tables.filter(
            updates__latest__gte=thirty_days_ago, updates__entity__slug__in=["month", "week", "day"]
        )
        .distinct()
        .count()
    )

    aggregates = treated_tables.aggregate(
        total_size=Sum("uncompressed_file_size"), total_rows=Sum("number_rows")
    )

    data = {
        "datasets_with_treated_tables": datasets_with_treated_tables_count,
        "total_treated_tables": total_treated_tables_count,
        "updated_last_30_days": recent_tables_count,
        "total_size_bytes": aggregates["total_size"] or 0,
        "total_rows": aggregates["total_rows"] or 0,
    }

    return JsonResponse(data)


def columns_view(request: HttpRequest, table_id: str = None, column_id: str = None):
    """
    A simple REST API view for Columns.
    """
    if column_id:
        try:
            column = Column.objects.select_related("table", "table__dataset", "bigquery_type").get(
                id=column_id
            )
            data = serialize(
                "json",
                [column],
                fields=(
                    "name",
                    "description",
                    "bigquery_type",
                    "is_primary_key",
                    "table",
                ),
            )
            return HttpResponse(data, content_type="application/json")
        except Column.DoesNotExist:
            return JsonResponse({"error": "Column not found"}, status=404)
    elif table_id:
        columns = (
            Column.objects.filter(table_id=table_id)
            .select_related(
                "table",
                "table__dataset",
                "bigquery_type",
                "directory_primary_key__table__dataset",
            )
            .prefetch_related(
                "directory_primary_key__table__cloud_tables", "coverages__datetime_ranges"
            )
            .order_by("order")
        )

        if not columns.exists():
            return JsonResponse({"error": "Table not found or has no columns"}, status=404)

        results = []
        table_temporal_coverage = None
        for col in columns:
            col_data = {
                "id": str(col.id),
                "order": col.order,
                "name": col.name,
                "description": col.description,
                "bigquery_type": {"name": col.bigquery_type.name if col.bigquery_type else None},
                "is_primary_key": col.is_primary_key,
                "covered_by_dictionary": col.covered_by_dictionary,
                "measurement_unit": col.measurement_unit,
                "contains_sensitive_data": col.contains_sensitive_data,
                "observations": col.observations,
                "temporal_coverage": None,
                "directory_primary_key": None,
            }

            col_coverage = get_temporal_coverage([col])
            if not col_coverage.get("start") and not col_coverage.get("end"):
                if table_temporal_coverage is None:
                    table_temporal_coverage = col.table.temporal_coverage_from_table
                col_data["temporal_coverage"] = table_temporal_coverage
            else:
                col_data["temporal_coverage"] = col_coverage

            if dpk := col.directory_primary_key:
                cloud_table = dpk.table.cloud_tables.first()
                col_data["directory_primary_key"] = {
                    "id": str(dpk.id),
                    "name": dpk.name,
                    "table": {
                        "id": str(dpk.table.id),
                        "name": dpk.table.name,
                        "is_closed": dpk.table.is_closed,
                        "uncompressed_file_size": dpk.table.uncompressed_file_size,
                        "dataset": {
                            "id": str(dpk.table.dataset.id),
                            "name": dpk.table.dataset.name,
                        },
                        "cloud_table": {
                            "gcp_table_id": cloud_table.gcp_table_id,
                            "gcp_dataset_id": cloud_table.gcp_dataset_id,
                            "gcp_project_id": cloud_table.gcp_project_id,
                        }
                        if cloud_table
                        else None,
                    },
                }
            results.append(col_data)

        return JsonResponse(results, safe=False)
    else:
        columns = Column.objects.all()[:100]
        data = serialize(
            "json",
            columns,
            fields=("id", "name", "table"),
        )
        return HttpResponse(data, content_type="application/json")
