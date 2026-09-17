# -*- coding: utf-8 -*-
import re
from typing import Dict, List

import pandas as pd
from django.db import transaction
from django.http import JsonResponse
from django.views import View
from loguru import logger

from backend.apps.api.v1.models import BigQueryType, Column, Table

logger = logger.bind(module="admin_data_tools.column_import")


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
