# -*- coding: utf-8 -*-
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class Metadata(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class ColumnMetadata(Metadata):
    name: str = Field(description="BigQuery column name")
    type: str = Field(description="BigQuery column name")
    description: str | None = Field(default=None, description="BigQuery column description")


class TableMetadata(Metadata):
    id: str = Field(description="BigQuery table id")
    full_table_id: str = Field(
        description="BigQuery table_id in the format project_id.dataset_id.table_id"
    )
    name: str = Field(description="Table name")
    description: str | None = Field(default=None, description="Table description")
    columns: list[ColumnMetadata] = Field(description="List of columns for this table")


class DatasetMetadata(Metadata):
    id: str = Field(description="BigQuery dataset id")
    name: str = Field(description="Dataset name")
    description: str | None = Field(default=None, description="Dataset description")
    tables: list[TableMetadata] = Field(description="List of tables for this dataset")


class MetadataFormatter(Protocol):
    @staticmethod
    def format_dataset_metadata(dataset: DatasetMetadata) -> str:
        ...

    @staticmethod
    def format_table_metadata(table: TableMetadata) -> str:
        ...


class MarkdownMetadataFormatter:
    @staticmethod
    def format_dataset_metadata(dataset: DatasetMetadata) -> str:
        """Return formatted dataset metadata in markdown.

        Args:
            dataset (DatasetMetadata): An object containing dataset metadata.

        Returns:
            str: Formatted metadata for the given dataset.
        """
        # Dataset name and description
        metadata = f"# {dataset.id}\n\n### Description:\n{dataset.description}\n\n"

        # Dataset tables
        metadata += "### Tables:\n"
        tables_metadata = [
            f"- {table.full_table_id}: {table.description}" for table in dataset.tables
        ]

        metadata += "\n\n".join(tables_metadata)

        return metadata

    @staticmethod
    def format_table_metadata(table: TableMetadata) -> str:
        """Return formatted table metadata in markdown.

        Args:
            table (TableMetadata): An object containing table metadata.

        Returns:
            str: Formatted metadata for the given table.
        """
        # Table name and description
        metadata = f"# {table.id}\n\n### Description:\n{table.description}\n\n"

        # Table schema
        metadata += "### Schema:\n"
        fields = "\n\t".join([f"{field.name} {field.type}" for field in table.columns])
        metadata += f"CREATE TABLE {table.id} (\n\t{fields}\n)\n\n"

        # Table columns details
        metadata += "### Column Details:\n"
        header = "|column name|column type|column description|\n|---|---|---|"
        lines = "\n".join(
            [f"|{field.name}|{field.type}|{field.description}|" for field in table.columns]
        )

        if lines:
            metadata += f"{header}\n{lines}"
        else:
            metadata += header

        return metadata
