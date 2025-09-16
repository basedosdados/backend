# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, List
from urllib.parse import urlparse

import pandas as pd
from django.core.serializers import serialize
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.views import View

from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone  

from backend.apps.api.v1.models import (
    BigQueryType,
    CloudTable,
    Column,
    get_temporal_coverage,
    Dataset,
    Table,
)

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


def upload_columns(request: HttpRequest):
    # Aqui vai sua função

    token, table_id, dataset_id, link = request.POST.values()

    selected_table = Table.objects.get(id=table_id)

    selected_table.columns.all().delete()

    architecture = read_architecture_table(link)

    tables_dict: Dict[str, Table] = {table.gbq_slug: table for table in Table.objects.all()}

    columns: List[Column] = [
        create_columns(selected_table=selected_table, tables_dict=tables_dict, row=row)
        for _, row in architecture.iterrows()
    ]

    selected_table.columns.set(columns)

    resultado = "Colunas Salvas com sucesso!"

    print(token, table_id, dataset_id, link)

    return JsonResponse({"status": "sucesso", "mensagem": resultado})


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
    # Pegar ID do BigQueryType Model

    row_bqtype = row["bigquery_type"].strip().upper()
    bqtype = BigQueryType.objects.get(name=row_bqtype)

    # Pegar ID da coluna Diretorio

    directory_column = None

    if row["directory_column"]:
        full_slug_models = "basedosdados.{table_full_slug}"

        table_full_slug = row["directory_column"].split(":")[0]
        table_full_slug = full_slug_models.format(table_full_slug=table_full_slug)

        directory_column_name = row["directory_column"].split(":")[1]

        table_directory = tables_dict[table_full_slug]

        directory_column = table_directory.columns.get(name=directory_column_name)

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
    treated_tables = Table.objects.exclude(
        status__slug__in=["under_review", "excluded"]
    ).exclude(
        slug__in=["dicionario", "dictionary"]
    ).exclude(
        dataset__status__slug__in=["under_review", "excluded"]
    )

    datasets_with_treated_tables_count = treated_tables.values_list(
        'dataset_id', flat=True
    ).distinct().count()

    total_treated_tables_count = treated_tables.count()

    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_tables_count = treated_tables.filter(
        updates__latest__gte=thirty_days_ago,
        updates__entity__slug__in=['month', 'week', 'day']
    ).distinct().count()

    aggregates = treated_tables.aggregate(
        total_size=Sum("uncompressed_file_size"),
        total_rows=Sum("number_rows")
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
            column = Column.objects.select_related(
                "table", "table__dataset", "bigquery_type"
            ).get(id=column_id)
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
                "directory_primary_key__table__cloud_tables",
                "coverages__datetime_ranges"
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
                        "cloud_table": {"gcp_table_id": cloud_table.gcp_table_id, "gcp_dataset_id": cloud_table.gcp_dataset_id, "gcp_project_id": cloud_table.gcp_project_id} if cloud_table else None
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