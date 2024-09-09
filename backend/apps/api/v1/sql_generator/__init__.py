# -*- coding: utf-8 -*-
import json
from textwrap import dedent

from backend.apps.api.v1.models import CloudTable, Column, Table

# Loading the map of directory description columns
with open("backend/apps/api/v1/sql_generator/directory_description.json") as f:
    map_directory_description_column = json.load(f)


class OneBigTableQueryGenerator:
    """
    Class to generate a one big table query.
    """

    def has_directory(self, column: Column):
        """
        Verify if a column has a directory and is not a temporal directory.
        """
        return (
            column.dir_column
            and column.dir_cloud_table
            and "diretorios_data_tempo" not in str(column.dir_cloud_table)
        )

    def get_directory_description_column(self, column: Column, cloud_table: CloudTable):
        """
        Get cte column name with adjustments
        """
        name = f"{cloud_table.gcp_suffix_id}.{column.dir_column.name}"
        return map_directory_description_column.get(name)

    def get_components_by_dictionary(self, table: Table, column: Column):
        """
        Get the column components by dictionary
        """
        sql_cte_table = f"dicionario_{column.name}"
        sql_cte = f"""
            {sql_cte_table} AS (
                SELECT
                    chave AS chave_{column.name},
                    valor AS descricao_{column.name}
                FROM `{table.gbq_dict_slug}`
                WHERE
                    TRUE
                    AND nome_coluna = '{column.name}'
                    AND id_tabela = '{table.gbq_table_slug}'
            )"""
        sql_join = f"""
            LEFT JOIN `{sql_cte_table}`
                ON dados.{column.name} = chave_{column.name}"""
        sql_select = f"descricao_{column.name} AS {column.name}"

        self.sql_ctes.append(dedent(sql_cte))
        self.sql_joins.append(dedent(sql_join))
        self.sql_selects.append(dedent(sql_select))

    def get_components_by_directory(self, column: Column):
        """
        Get the column components by directory
        """
        sql_cte_table = f"diretorio_{column.name}"
        sql_cte_column = self.get_directory_description_column(column, column.dir_cloud_table)
        sql_select_label = [
            f"{sql_cte_table}.{sql_cte_column} AS {column.name}_{sql_cte_column}"
            for sql_cte_column in sql_cte_column
        ]

        sql_select_id = f"dados.{column.name} AS {column.name}"

        sql_from = f" FROM `{column.dir_cloud_table}`) AS {sql_cte_table}"
        columns_names = ",".join(sql_cte_column)
        sql_join = f"""
            LEFT JOIN (SELECT DISTINCT {column.dir_column.name},{columns_names} {sql_from}
                ON dados.{column.name} = {sql_cte_table}.{column.dir_column.name}"""
        self.sql_joins.append(dedent(sql_join))
        self.sql_selects.append(dedent(sql_select_id))

        if isinstance(sql_select_label, list):
            self.sql_selects.extend([dedent(sql_select) for sql_select in sql_select_label])
        else:
            self.sql_selects.append(dedent(sql_select_label))

    def get_components(
        self, table: Table, columns: list[str] = None, include_table_translation: bool = True
    ):
        column: Column
        for column in table.columns.order_by("order").all():
            # Skip columns that are not in the list if it is provided
            if columns and column.name not in columns:
                continue

            if column.covered_by_dictionary and include_table_translation:
                self.get_components_by_dictionary(table, column)

            elif self.has_directory(column) and include_table_translation:
                self.get_components_by_directory(column)

            else:
                self.sql_selects.append(f"dados.{column.name} as {column.name}")

    def generate(
        self, table: Table, columns: list[str] = None, include_table_translation: bool = True
    ):
        """
        Get a denormalized sql query, similar to a one big table
        """
        self.sql_ctes = []
        self.sql_joins = []
        self.sql_selects = []

        self.get_components(table, columns, include_table_translation)

        sql_ctes = "WITH " + ",".join(self.sql_ctes) if self.sql_ctes else ""
        sql_joins = "".join(self.sql_joins) if self.sql_joins else ""
        sql_selects = "\nSELECT\n    " + ",\n    ".join(self.sql_selects)
        sql_from = f"\nFROM `{table.gbq_slug}` AS dados"

        return sql_ctes + sql_selects + sql_from + sql_joins
