# -*- coding: utf-8 -*-
import json
import os
from functools import cache
from typing import Any, Literal, Optional, Self

import httpx
from google.api_core import exceptions
from google.cloud import bigquery as bq
from langchain_core.tools import tool
from pydantic import BaseModel, model_validator

SEARCH_URL = "https://backend.basedosdados.org/search/"
GRAPHQL_URL = "https://backend.basedosdados.org/graphql"

DATASET_DETAILS_QUERY = """
query GetDatasetOverview($id: ID!) {
    allDataset(id: $id, first: 1) {
        edges {
            node {
                id
                name
                slug
                description
                organizations {
                    edges {
                        node {
                            name
                            slug
                        }
                    }
                }
                themes {
                    edges {
                        node {
                            name
                        }
                    }
                }
                tags {
                    edges {
                        node {
                            name
                        }
                    }
                }
                tables {
                    edges {
                        node {
                            id
                            name
                            slug
                            description
                            cloudTables {
                                edges {
                                    node {
                                        gcpProjectId
                                        gcpDatasetId
                                        gcpTableId
                                    }
                                }
                            }
                            columns {
                                edges {
                                    node {
                                        id
                                        name
                                        description
                                        bigqueryType {
                                            name
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
"""


class Column(BaseModel):
    name: str
    type: str
    description: Optional[str]


class Table(BaseModel):
    id: str
    gcp_id: Optional[str]
    name: str
    slug: Optional[str]
    description: Optional[str]
    columns: list[Column]


class DatasetOverview(BaseModel):
    id: str
    name: str
    slug: Optional[str]
    description: Optional[str]
    tags: list[str]
    themes: list[str]
    organizations: list[str]


class Dataset(DatasetOverview):
    tables: list[Table]


class ToolOutput(BaseModel):
    status: Literal["success", "error"]
    results: Optional[Any] = None
    error_details: Optional[dict[str, Any]] = None

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        if (self.results is None) ^ (self.error_details is None):
            return self
        raise ValueError("Only one of 'results' or 'error_details' should be set")


@cache
def get_bigquery_client():
    return bq.Client(project=os.environ["QUERY_PROJECT_ID"])


@tool
def search_datasets(query: str) -> str:
    """Search for datasets in Base dos Dados using keywords.

    CRITICAL: Use individual KEYWORDS only, not full sentences. The search engine uses Elasticsearch.

    Args:
        query (str): 2-3 keywords maximum. Use Portuguese terms, organization acronyms, or dataset acronyms.
            Good Examples: "censo", "educacao", "ibge", "inep", "rais", "saude"
            Avoid: "Brazilian population data by municipality"

    Returns:
        str: JSON array of datasets. If empty/irrelevant results, try different keywords.

    Strategy: Start with broad terms like "censo", "ibge", "inep", "rais", then get specific if needed.
    Next step: Use `get_dataset_details()` with returned dataset IDs.
    """  # noqa: E501
    try:
        with httpx.Client() as client:
            response = client.get(
                url=SEARCH_URL,
                params={"q": query, "page_size": 10},
                timeout=httpx.Timeout(5.0, read=60.0),
            )
            response.raise_for_status()
            data: dict = response.json()

        datasets = data.get("results", [])

        overviews = []

        for dataset in datasets:
            dataset_overview = DatasetOverview(
                id=dataset["id"],
                name=dataset["name"],
                slug=dataset.get("slug"),
                description=dataset.get("description"),
                tags=[tag["name"] for tag in dataset.get("tags", [])],
                themes=[theme["name"] for theme in dataset.get("themes", [])],
                organizations=[org["name"] for org in dataset.get("organizations", [])],
            )
            overviews.append(dataset_overview.model_dump())

        tool_output = ToolOutput(status="success", results=overviews).model_dump(exclude_none=True)
    except Exception as e:
        tool_output = ToolOutput(
            status="error", error_details={"message": f"Error searching datasets:\n{e}"}
        ).model_dump(exclude_none=True)

    return json.dumps(tool_output, ensure_ascii=False, indent=2)


@tool
def get_dataset_details(dataset_id: str) -> str:
    """Get comprehensive details about a specific dataset including all tables and columns.

    Use AFTER `search_datasets()` to understand data structure before writing queries.

    Args:
        dataset_id (str): Dataset ID obtained from `search_datasets()`.
            This is typically a UUID-like string, not the human-readable name.

    Returns:
        str: JSON object with complete dataset information, including:
            - Basic metadata (name, description, tags, themes, organizations)
            - tables: Array of all tables in the dataset with:
                - gcp_id: Full BigQuery table reference (`project.dataset.table`)
                - columns: All column names, types, and descriptions
                - table descriptions explaining what each table contains

    Next step: Use `execute_bigquery_sql()` to execute queries.
    """  # noqa: E501
    try:
        with httpx.Client() as client:
            response = client.post(
                url=GRAPHQL_URL,
                json={
                    "query": DATASET_DETAILS_QUERY,
                    "variables": {"id": dataset_id},
                },
                timeout=httpx.Timeout(5.0, read=60.0),
            )
            response.raise_for_status()
            data: dict[str, dict[str, dict]] = response.json()

        dataset_edges = data.get("data", {}).get("allDataset", {}).get("edges", [])

        if not dataset_edges:
            return f"Dataset {dataset_id} not found"

        dataset = dataset_edges[0]["node"]

        dataset_id = dataset["id"]
        dataset_name = dataset["name"]
        dataset_slug = dataset.get("slug")
        dataset_description = dataset.get("description")

        # Tags
        dataset_tags = []
        for edge in dataset.get("tags", {}).get("edges", []):
            if tag := edge.get("node", {}).get("name"):
                dataset_tags.append(tag)

        # Themes
        dataset_themes = []
        for edge in dataset.get("themes", {}).get("edges", []):
            if theme := edge.get("node", {}).get("name"):
                dataset_themes.append(theme)

        # Organizations
        dataset_organizations = []
        for edge in dataset.get("organizations", {}).get("edges", []):
            if org := edge.get("node", {}).get("name"):
                dataset_organizations.append(org)

        # Tables
        dataset_tables = []
        for edge in dataset.get("tables", {}).get("edges", []):
            table = edge["node"]

            table_id = table["id"]
            table_name = table["name"]
            table_slug = table.get("slug")
            table_description = table.get("description")

            cloud_table_edges = table["cloudTables"]["edges"]
            if cloud_table_edges:
                cloud_table = cloud_table_edges[0]["node"]
                gcp_project_id = cloud_table["gcpProjectId"]
                gcp_dataset_id = cloud_table["gcpDatasetId"]
                gcp_table_id = cloud_table["gcpTableId"]
                table_gcp_id = f"{gcp_project_id}.{gcp_dataset_id}.{gcp_table_id}"
            else:
                table_gcp_id = None

            table_columns = []
            for edge in table["columns"]["edges"]:
                column = edge["node"]
                table_columns.append(
                    Column(
                        name=column["name"],
                        type=column["bigqueryType"]["name"],
                        description=column.get("description"),
                    )
                )

            dataset_tables.append(
                Table(
                    id=table_id,
                    gcp_id=table_gcp_id,
                    name=table_name,
                    slug=table_slug,
                    description=table_description,
                    columns=table_columns,
                )
            )

        dataset = Dataset(
            id=dataset_id,
            name=dataset_name,
            slug=dataset_slug,
            description=dataset_description,
            tags=dataset_tags,
            themes=dataset_themes,
            organizations=dataset_organizations,
            tables=dataset_tables,
        ).model_dump()

        tool_output = ToolOutput(status="success", results=dataset).model_dump(exclude_none=True)
    except Exception as e:
        tool_output = ToolOutput(
            status="error", error_details={"message": f"Error fetching dataset details:\n{e}"}
        ).model_dump(exclude_none=True)

    return json.dumps(tool_output, ensure_ascii=False, indent=2)


@tool
def execute_bigquery_sql(sql_query: str) -> str:
    """Execute a SQL query against BigQuery tables from the Base dos Dados database.

    Use AFTER identifying the right datasets and understanding tables structure.
    It includes a 20GB processing limit for safety.

    Args:
        sql_query (str): Standard GoogleSQL query. Must reference
            tables using their full `gcp_id` from `get_dataset_details()`.

    Best practices:
        - Use fully qualified names: `project.dataset.table`
        - Select only needed columns, avoid `SELECT *`
        - Add `LIMIT` for exploration
        - Filter early with `WHERE` clauses
        - Order by relevant columns
        - Never use DDL/DML commands
        - Use appropriate data types in comparisons

    Returns:
        str: Query results as JSON array. Empty results return "[]".
    """  # noqa: E501
    client = get_bigquery_client()

    try:
        job_config = bq.QueryJobConfig(dry_run=True, use_query_cache=False)
        query_job = client.query(sql_query, job_config=job_config)

        limit_bytes = 20e9  # 20GB limit for queries
        total_bytes = query_job.total_bytes_processed

        if total_bytes and total_bytes > limit_bytes:
            tool_output = ToolOutput(
                status="error",
                error_details={
                    "type": "QueryTooLarge",
                    "limit_bytes": limit_bytes,
                    "total_processed_bytes": total_bytes,
                    "message": (
                        "Query aborted: Data processed exceeds the 20GB per-query limit. "
                        "Consider optimizing by adding filters, selecting fewer columns, "
                        "or using a LIMIT clause before retrying."
                    ),
                },
            )
            return tool_output.model_dump_json(indent=2, exclude_none=True)

        rows = client.query(sql_query).result()

        results = [dict(row) for row in rows]

        tool_output = ToolOutput(status="success", results=results).model_dump(exclude_none=True)
    except Exception as e:
        tool_output = ToolOutput(
            status="error", error_details={"message": f"SQL query execution failed:\n{e}"}
        ).model_dump(exclude_none=True)

    return json.dumps(tool_output, ensure_ascii=False, default=str)


@tool
def decode_table_values(table_gcp_id: str, column_name: Optional[str] = None) -> str:
    """Decode coded values from a table.

    Use when column values appear to be codes (e.g., 1,2,3 or A,B,C).
    Many datasets use codes for storage efficiency. This tool provides
    the authoritative meanings of these codes.

    Args:
        table_gcp_id (str): Full BigQuery table reference
        column_name (Optional[str], optional): Column with coded values. If `None`,
            all columns will be used. Defaults to `None`.

    Returns:
        str: JSON array with chave (code) and valor (meaning) mappings.
    """  # noqa: E501
    client = get_bigquery_client()

    try:
        project_name, dataset_name, table_name = table_gcp_id.split(".")
    except ValueError:
        return ToolOutput(
            status="error",
            error_details={
                "message": (
                    f"{table_gcp_id} is not a valid table reference. "
                    "Please, provide a valid table reference in the format `project.dataset.table`"
                )
            },
        ).model_dump_json(indent=2, exclude_none=True)

    dataset_id = f"{project_name}.{dataset_name}"
    dict_table_id = f"{dataset_id}.dicionario"

    search_query = f"""
        SELECT nome_coluna, chave, valor
        FROM {dict_table_id}
        WHERE id_tabela = '{table_name}'
    """

    if column_name is not None:
        search_query += f"AND nome_coluna = '{column_name}'"

    search_query += "ORDER BY nome_coluna, chave"

    try:
        job_config = bq.QueryJobConfig(dry_run=True, use_query_cache=False)
        query_job = client.query(search_query, job_config=job_config)

        limit_bytes = 1e9  # 1GB limit for dictionary queries
        total_bytes = query_job.total_bytes_processed

        if total_bytes and total_bytes > limit_bytes:
            return ToolOutput(
                status="error",
                error_details={
                    "type": "QueryTooLarge",
                    "limit_bytes": limit_bytes,
                    "total_processed_bytes": total_bytes,
                    "message": (
                        "Dictionary table is unexpectedly large. "
                        "This might not be the right approach. "
                        "Check if this dataset actually uses "
                        "encoded values or try a different table."
                    ),
                },
            ).model_dump_json(indent=2, exclude_none=True)

        rows = client.query(search_query).result()
        results = [dict(row) for row in rows]
        tool_output = ToolOutput(status="success", results=results).model_dump(exclude_none=True)
    except exceptions.NotFound:
        return ToolOutput(
            status="error",
            error_details={
                "type": "TableNotFound",
                "message": (
                    f"Dictionary table not found for dataset {dataset_id}. "
                    "This indicates this dataset does not contain a dicionary table. "
                    "Consider using the `inspect_column_values` tool to inspect column values."
                ),
            },
        ).model_dump_json(indent=2, exclude_none=True)
    except Exception as e:
        tool_output = ToolOutput(
            status="error", error_details={"message": f"Failed to decode table values:\n{e}"}
        ).model_dump(exclude_none=True)

    return json.dumps(tool_output, ensure_ascii=False, default=str)


@tool
def inspect_column_values(table_gcp_id: str, column_name: str, limit: int = 100) -> str:
    """Show actual distinct values in a column.

    FALLBACK tool to use when `search_dictionary_table()` fails.
    Useful for understanding data patterns and planning `WHERE` clauses.

    Args:
        table_gcp_id (str): Full BigQuery table reference
        column_name (str): Column name from `get_dataset_details()`
        limit (int, optional): Max distinct values to return (default: 100)

    Returns:
        str: JSON array of distinct values.
    """  # noqa: E501
    client = get_bigquery_client()

    sql_query = f"SELECT DISTINCT {column_name} FROM {table_gcp_id} LIMIT {limit}"

    try:
        job_config = bq.QueryJobConfig(dry_run=True, use_query_cache=False)
        query_job = client.query(sql_query, job_config=job_config)

        limit_bytes = 5e9  # 5GB limit for inspection queries
        total_bytes = query_job.total_bytes_processed

        if total_bytes and total_bytes > limit_bytes:
            return ToolOutput(
                status="error",
                error_details={
                    "status": "error",
                    "type": "QueryTooLarge",
                    "limit_bytes": limit_bytes,
                    "total_processed_bytes": total_bytes,
                    "message": (
                        "Column inspection exceeds the 5GB per-query limit for inspection. "
                        "Try a smaller limit or add WHERE filters to reduce data size."
                    ),
                },
            ).model_dump_json(indent=2, exclude_none=True)

        rows = client.query(sql_query).result()

        results = [row.get(column_name) for row in rows]

        tool_output = ToolOutput(status="success", results=results).model_dump(exclude_none=True)
    except Exception as e:
        tool_output = ToolOutput(
            status="error", error_details={"message": f"Failed to inspect colum values:\n{e}"}
        ).model_dump(exclude_none=True)

    return json.dumps(tool_output, ensure_ascii=False, default=str)
