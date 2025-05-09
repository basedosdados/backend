import json
import os

import cachetools.func
from google.cloud import bigquery as bq
from loguru import logger

from backend.apps.api.v1.models import Dataset

from .metadata_formatter import *


class ChatbotDatabase:
    """A BigQuery-backed database interface with local metadata support.

    This class provides methods to:
      - Retrieve and format metadata about datasets, tables, and columns
      - Execute SQL queries on BigQuery

    Optionally uses a custom metadata formatter; defaults to Markdown formatting.

    Args:
        billing_project (str | None):
            GCP project ID for billing. Falls back to the `BILLING_PROJECT_ID` environment variable if not provided.
        query_project (str | None):
            GCP project ID for executing queries. Falls back to the `QUERY_PROJECT_ID` environment variable if not provided.
        metadata_formatter (MetadataFormatter | None):
            Custom formatter for metadata. Defaults to `MarkdownMetadataFormatter`.
    """

    def __init__(
        self,
        billing_project: str | None = None,
        query_project: str | None = None,
        metadata_formatter: MetadataFormatter | None = None,
    ):
        billing_project = billing_project or os.getenv('BILLING_PROJECT_ID')
        query_project = query_project or os.getenv('QUERY_PROJECT_ID')

        self._client = bq.Client(billing_project)
        self._project = query_project

        if metadata_formatter is not None:
            self.formatter = metadata_formatter
        else:
            self.formatter = MarkdownMetadataFormatter()

    @staticmethod
    @cachetools.func.ttl_cache(ttl=60*60*24)
    def _get_metadata() -> list[DatasetMetadata]:
        """Fetch and return metadata for all datasets and their associated tables and columns.
        The metadata includes dataset and table IDs and descriptions, and column information
        such as name, type, and description. The result is cached for 24 hours.

        Returns:
            list[DatasetMetadata]: A list of metadata objects, one for each dataset with at least one valid table.
        """
        datasets = Dataset.objects.prefetch_related(
            "tables__cloud_tables__columns__bigquery_type"
        )

        datasets_metadata: list[DatasetMetadata] = []

        for dataset in datasets:
            gcp_dataset_id = None
            tables_metadata: list[TableMetadata] = []

            for table in dataset.tables.all():
                # There must be only a single CloudTable for a given Table
                cloud_table = table.cloud_tables.first()

                if cloud_table is None:
                    continue

                if gcp_dataset_id is None:
                    gcp_dataset_id = cloud_table.gcp_dataset_id

                columns_metadata = [
                    ColumnMetadata(
                        name=column.name,
                        type=column.bigquery_type.name,
                        description=column.description,
                    )
                    for column in cloud_table.columns.all()
                ]

                full_table_id = f"{cloud_table.gcp_project_id}.{cloud_table.gcp_dataset_id}.{cloud_table.gcp_table_id}"

                tables_metadata.append(
                    TableMetadata(
                        id=cloud_table.gcp_table_id,
                        full_table_id=full_table_id,
                        name=table.name,
                        description=table.description,
                        columns=columns_metadata
                    )
                )

                # TODO: Get some sample rows for each table

            if tables_metadata:
                datasets_metadata.append(
                    DatasetMetadata(
                        id=gcp_dataset_id,
                        name=dataset.name,
                        description=dataset.description,
                        tables=tables_metadata
                    )
                )

        return datasets_metadata

    def get_datasets_info(self) -> str:
        """Return formatted metadata for all datasets in a BigQuery project.

        Returns:
            str: A formatted string containing metadata for the datasets.
        """
        datasets_info = [
            self.formatter.format_dataset_metadata(dataset)
            for dataset in self._get_metadata()
        ]

        return "\n\n---\n\n".join(datasets_info)

    def get_tables_info(self, dataset_names: str) -> str:
        """Return formatted metadata for all tables in one or more BigQuery datasets.

        Args:
            dataset_names (str): A comma-separated list of BigQuery dataset IDs.

        Returns:
            str: A formatted string containing metadata for the tables in the specified datasets.
        """
        dataset_ids = {id.strip() for id in dataset_names.split(",")}

        datasets = [
            dataset for dataset in self._get_metadata() if dataset.id in dataset_ids
        ]

        tables_info = []

        for dataset in datasets:
            tables_info.append(
                "\n\n".join([self.formatter.format_table_metadata(table) for table in dataset.tables])
            )

        return "\n\n---\n\n".join(tables_info)

    def query(self, query: str) -> str:
        """Execute a SQL query using BigQuery and return the results as a JSON string.

        Args:
            query (str): The SQL query to execute.

        Raises:
            Exception: Propagates any exceptions raised during query execution.

        Returns:
            str: A JSON-formatted string representing the query results. Returns an empty string if no results are found.
        """
        try:
            rows = self._client.query(query, project=self._project).result()

            results = [dict(row) for row in rows]

            if results:
                return json.dumps(results, ensure_ascii=False, default=str)
            return ""
        except Exception as e:
            logger.exception("Error on querying table:")
            raise e
