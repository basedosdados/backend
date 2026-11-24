# -*- coding: utf-8 -*-
import csv
import io

from django.http import HttpResponse
from django.views import View

from backend.apps.api.v1.models import Table

LOCALES = ("pt", "en", "es")

HEADERS = {
    "pt": [
        "Nome do Conjunto de Dados",
        "Descrição do Conjunto de Dados",
        "Nome Tabela",
        "Descrição Tabela",
        "Disponibilidade dos dados",
        "Número de linhas da tabela",
        "Cobertura temporal (anos e meses que temos dados disponíveis)",
    ],
    "en": [
        "Dataset Name",
        "Dataset Description",
        "Table Name",
        "Table Description",
        "Data Availability",
        "Number of rows in the table",
        "Temporal coverage (years and months for which data is available)",
    ],
    "es": [
        "Nombre del Conjunto de Datos",
        "Descripción del Conjunto de Datos",
        "Nombre de la Tabla",
        "Descripción de la Tabla",
        "Disponibilidad de los datos",
        "Número de filas de la tabla",
        "Cobertura temporal (años y meses para los cuales hay datos disponibles)",
    ],
}

STATUS_MAP = {
    "pt": {
        "closed": "Parcialmente ou totalmente pago",
        "open": "Totalmente grátis",
        "to": " a ",
    },
    "en": {
        "closed": "Partially or totally paid",
        "open": "Totally free",
        "to": " to ",
    },
    "es": {
        "closed": "Parcial o totalmente de pago",
        "open": "Totalmente gratis",
        "to": " a ",
    },
}


def _get_catalog_tables():
    """Busca as tabelas ativas do catálogo com os prefetches da exportação.

    Returns:
        QuerySet de Table com dataset e as relações de cobertura/colunas
        usadas para montar o CSV sem disparar uma query por tabela.
    """
    return (
        Table.objects.select_related("dataset")
        .prefetch_related(
            "coverages", "coverages__datetime_ranges", "columns", "columns__coverages"
        )
        .exclude(status__slug__in=["under_review", "excluded"])
        .exclude(dataset__status__slug__in=["under_review", "excluded"])
        .order_by("dataset__name")
    )


def generate_catalog_csv(locale: str = "pt") -> bytes:
    """Gera o CSV do catálogo completo de tabelas para um idioma.

    Args:
        locale: Idioma do cabeçalho e dos campos traduzidos ("pt", "en" ou
            "es"). Qualquer outro valor cai para "pt".

    Returns:
        Conteúdo do CSV codificado em UTF-8.
    """
    if locale not in LOCALES:
        locale = "pt"

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(HEADERS[locale])

    for table in _get_catalog_tables():
        table_coverage_is_closed = any(c.is_closed for c in table.coverages.all())
        column_coverage_is_closed = any(
            any(cc.is_closed for cc in col.coverages.all()) for col in table.columns.all()
        )
        size_is_closed = (
            table.uncompressed_file_size
            and 100 * 1024 * 1024 < table.uncompressed_file_size <= 1000 * 1024 * 1024
        )
        has_closed_coverage = (
            table_coverage_is_closed or column_coverage_is_closed or size_is_closed
        )

        data_status = (
            STATUS_MAP[locale]["closed"] if has_closed_coverage else STATUS_MAP[locale]["open"]
        )

        temporal_coverage = getattr(table, "temporal_coverage", {}) or {}
        start = temporal_coverage.get("start")
        end = temporal_coverage.get("end")
        temporal_coverage_str = f"{start}{STATUS_MAP[locale]['to']}{end}" if start and end else ""

        dataset_name = ""
        dataset_desc = ""
        if table.dataset:
            dataset_name = getattr(table.dataset, f"name_{locale}", None) or table.dataset.name
            dataset_desc = (
                getattr(table.dataset, f"description_{locale}", None) or table.dataset.description
            )

        table_name = getattr(table, f"name_{locale}", None) or table.name
        table_desc = getattr(table, f"description_{locale}", None) or table.description

        writer.writerow(
            [
                dataset_name,
                dataset_desc,
                table_name,
                table_desc,
                data_status,
                table.number_rows if table.number_rows is not None else "",
                temporal_coverage_str,
            ]
        )

    return buffer.getvalue().encode("utf-8")


class ExportTablesView(View):
    def get(self, request, *args, **kwargs):
        """Serve o CSV do catálogo completo de tabelas para download.

        Args:
            request: Requisição HTTP; aceita o parâmetro de query `locale`
                ("pt", "en" ou "es").

        Returns:
            HttpResponse com o CSV como anexo (`catalog_bd.csv`).
        """
        locale = request.GET.get("locale", "pt")
        if locale not in LOCALES:
            locale = "pt"

        response = HttpResponse(generate_catalog_csv(locale), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="catalog_bd.csv"'
        return response
